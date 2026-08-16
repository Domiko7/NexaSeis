import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from nexaseis.common import get_config, ws_queue, db_queue, datalink_queue, seedlink_queue, stations
from nexaseis.calc import process_packets
from nexaseis.uvicorn import stations_api

BUFFER_TARGET_SIZE = 70
DEFAULT_SAMPLE_RATE = 100

_CHANNEL_BUFFERS = defaultdict(lambda: {"start_time": None, "waveform": []})
_STATION_CHANNELS = defaultdict(dict)


def load_stations() -> None:
    config = get_config()
    for stn in config.get("stations", []):
        key = (stn["network"], stn["code"], stn["location"])
        stations[key] = stn


def _dispatch_packet(packet: dict) -> None:
    modified_packet = packet.copy()
    del modified_packet["acceleration"]
    del modified_packet["velocity"]
    del modified_packet["displacement"]
    del modified_packet["waveform"]
    station = packet["station"]
    station_key = f"{station['network']}.{station['code']}.{station['location']}"
    channel_packets = _STATION_CHANNELS[station_key]
    channel_packets[station["channel"]] = modified_packet

    preferred_channel = sorted(
        channel_packets,
        key=lambda channel: (not channel.endswith("Z"), channel),
    )[0]
    aggregate = dict(channel_packets[preferred_channel])
    aggregate["timestamp"] = max(item["timestamp"] for item in channel_packets.values())
    for metric in ("pga", "pgv", "pgd"):
        aggregate[metric] = max(item[metric] for item in channel_packets.values())
    aggregate["channels"] = dict(channel_packets)
    stations_api[station_key] = aggregate

    for q in (ws_queue, db_queue, datalink_queue, seedlink_queue):
        try:
            q.put_nowait(packet)
        except asyncio.QueueFull:
            pass


async def _process_and_dispatch(packet: dict) -> None:
    num_samples = len(packet["waveform"])
    if not num_samples:
        return

    sample_rate = packet["station"].get("sample_rate") or DEFAULT_SAMPLE_RATE

    time_array = [i / sample_rate for i in range(num_samples)]
    sensitivity = packet["station"].get("sensitivity") or 1.0

    processed_packet = await asyncio.to_thread(
        process_packets, packet, time_array, sensitivity
    )

    _dispatch_packet(processed_packet)


async def handle_station(packet: dict) -> None:
    net = packet["station"]["network"]
    code = packet["station"]["code"]
    loc = packet["station"]["location"]
    chan = packet["station"]["channel"]

    matched_station = stations.get((net, code, loc))
    
    if matched_station:
        channel_info = matched_station.get("channels", {}).get(chan, {})
        
        if isinstance(channel_info, dict):
            sensitivity = channel_info.get("sensitivity")
            sample_rate = channel_info.get("sample_rate", DEFAULT_SAMPLE_RATE)
        else:
            sensitivity = channel_info
            sample_rate = DEFAULT_SAMPLE_RATE

        packet["station"]["sensitivity"] = sensitivity
        packet["station"]["sample_rate"] = sample_rate
        packet["station"]["name"] = matched_station.get("name", "")
        packet["station"]["lat"] = matched_station.get("lat", 0.0)
        packet["station"]["lon"] = matched_station.get("lon", 0.0)
    else:
        packet["station"]["sensitivity"] = None
        packet["station"]["sample_rate"] = DEFAULT_SAMPLE_RATE

    sample_rate = packet["station"]["sample_rate"]
    channel_key = (net, code, loc, chan)

    packet_time = datetime.fromtimestamp(packet["timestamp"], tz=timezone.utc)
    incoming_waveform = packet["waveform"]

    buffer = _CHANNEL_BUFFERS[channel_key]

    if buffer["start_time"] is None:
        buffer["start_time"] = packet_time
    else:
        expected_next_time = buffer["start_time"] + timedelta(seconds=len(buffer["waveform"]) / sample_rate)
        time_delta = abs((packet_time - expected_next_time).total_seconds())
        
        if time_delta > (1.5 / sample_rate) and buffer["waveform"]:
            logging.debug(f"Time gap detected for {channel_key} ({time_delta:.4f}s). Flushing partial packet.")
            out_packet = dict(packet)
            out_packet["timestamp"] = buffer["start_time"].timestamp()
            out_packet["waveform"] = buffer["waveform"]
            
            await _process_and_dispatch(out_packet)

            buffer["waveform"] = []
            buffer["start_time"] = packet_time

    buffer["waveform"].extend(incoming_waveform)

    while len(buffer["waveform"]) >= BUFFER_TARGET_SIZE:
        chunk = buffer["waveform"][:BUFFER_TARGET_SIZE]
        buffer["waveform"] = buffer["waveform"][BUFFER_TARGET_SIZE:]
        
        out_packet = dict(packet)
        out_packet["timestamp"] = buffer["start_time"].timestamp()
        out_packet["waveform"] = chunk
        
        await _process_and_dispatch(out_packet)

        buffer["start_time"] += timedelta(seconds=BUFFER_TARGET_SIZE / sample_rate)

    if not buffer["waveform"]:
        buffer["start_time"] = None
