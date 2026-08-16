import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from xml.etree.ElementTree import Element, SubElement, tostring

import simplemseed

from nexaseis.common import get_config, seedlink_queue, conn
from nexaseis.station import stations

SOFTWARE = "NexaSeis SeedLink"
RELEASE = (
    "SeedLink v3.1 NexaSeis Edition :: "
    "SLPROTO:3.1 CAP EXTREPLY NSWILDCARD BATCH WS:13"
)

CHUNK_SIZE = 100
SAMPLE_RATE = 100

INFO_CHUNK_SIZE = 448

RES_OK = b"OK\r\n"
RES_ERR = b"ERROR\r\n"

CAPABILITIES = (
    "dialup",
    "multistation",
    "window-extraction",
    "info",
    "info:id",
    "info:capabilities",
    "info:stations",
    "info:streams",
)

_START_TIME = datetime.now(timezone.utc)
_subscribers: dict[str, "SeedLinkConnection"] = {}
_CHANNEL_BUFFERS = defaultdict(lambda: {"start_time": None, "waveform": []})


class SeedLinkConnection:
    def __init__(self, writer: asyncio.StreamWriter, client_id: str):
        self.writer = writer
        self.client_id = client_id
        self.streaming = False
        self.station = ""
        self.network = ""
        self.location = "00"
        self.channels: list[tuple[str, str | None]] = []
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.sequence = 0
        self.out_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    def matches(self, network: str, code: str, location: str, channel: str) -> bool:
        if self.network and self.network != network:
            return False
        if self.station and self.station != code:
            return False
        if self.location and self.location != location:
            return False
        if not self.channels:
            return True
        for name, ctype in self.channels:
            if name != channel:
                continue
            if ctype and ctype != "D":
                continue
            return True
        return False


def _encode_seedlink_records(network, station, location, channel, sequence, start_time, sample_rate, samples):
    buf = bytearray()
    span = timedelta(seconds=1.0 / sample_rate)

    for i in range(0, len(samples), CHUNK_SIZE):
        chunk = samples[i:i + CHUNK_SIZE]
        chunk_start = start_time + span * i

        header = simplemseed.MiniseedHeader(
            network, station, location, channel, chunk_start, len(chunk), sample_rate,
            sequence_number=sequence % 1000000,
        )
        encoded = simplemseed.EncodedDataSegment(
            simplemseed.seedcodec.STEIM2, simplemseed.encodeSteim2(chunk), len(chunk), False
        )
        record = simplemseed.MiniseedRecord(header, data=encoded).pack()

        buf += f"SL{sequence % 0x1000000:06X}".encode("ascii")
        buf += record
        sequence += 1

    return sequence, bytes(buf)


def _station_element(root: Element, stn) -> Element:
    el = SubElement(root, "station")
    el.set("name", stn["code"])
    el.set("network", stn["network"])
    el.set("description", stn.get("name", ""))
    el.set("begin_seq", "000000")
    el.set("end_seq", "FFFFFF")
    return el


def _build_info_xml(level: str, config: dict) -> tuple[bytes, str]:
    root = Element("seedlink")
    root.set("software", SOFTWARE)
    root.set("organization", config.get("organization", ""))
    root.set("started", _START_TIME.strftime("%Y-%m-%d %H:%M:%S"))

    channel_code = "INF"
    if level == "ID":
        pass
    elif level in ("CAPABILITIES", "CONNECTIONS"):
        for name in CAPABILITIES:
            SubElement(root, "capability").set("name", name)
    elif level == "STATIONS":
        for stn in stations.values():
            _station_element(root, stn)
    elif level == "STREAMS":
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        for stn in stations.values():
            st_el = _station_element(root, stn)
            st_el.set("stream_check", "enabled")
            for chan in stn.get("channels", {}):
                str_el = SubElement(st_el, "stream")
                str_el.set("location", stn["location"])
                str_el.set("seedname", chan)
                str_el.set("type", "D")
                str_el.set("begin_time", _START_TIME.strftime("%Y-%m-%d %H:%M:%S"))
                str_el.set("end_time", now)
    else:
        channel_code = "ERR"

    xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>' + tostring(root)
    return xml_bytes, channel_code


def _pack_info_response(xml_bytes: bytes, channel_code: str) -> bytes:
    chunks = [xml_bytes[i:i + INFO_CHUNK_SIZE] for i in range(0, len(xml_bytes), INFO_CHUNK_SIZE)] or [b""]
    out = bytearray()

    for i, chunk in enumerate(chunks):
        final = i == len(chunks) - 1
        header = simplemseed.MiniseedHeader(
            "SL", "INFO", "  ", channel_code, _START_TIME, 0, 0.0,
            encoding=simplemseed.seedcodec.ASCII, sequence_number=i + 1,
        )
        record = simplemseed.MiniseedRecord(header, data=None, encodedDataBytes=chunk).pack()
        out += b"SLINFO " + (b"*" if not final else b" ")
        out += record

    return bytes(out)


def _query_history(network, station, location, channel_names, start_time, end_time):
    cur = conn.cursor()
    base = """
        SELECT s.channel, wp.timestamp, wp.waveform
        FROM waveform_packets wp
        JOIN stations s ON wp.station_id = s.id
        WHERE s.network = ? AND s.code = ? AND s.location = ?
          AND wp.timestamp BETWEEN ? AND ?
    """
    params = [network, station, location, start_time.timestamp(), end_time.timestamp()]

    if channel_names:
        placeholders = ",".join("?" * len(channel_names))
        base += f" AND s.channel IN ({placeholders})"
        params.extend(channel_names)

    base += " ORDER BY wp.timestamp ASC"

    cur.execute(base, params)
    return cur.fetchall()


async def _send_history(client: SeedLinkConnection) -> None:
    if client.start_time is None:
        return

    end_time = client.end_time or datetime.now(timezone.utc)
    channel_names = [name for name, _ in client.channels]

    try:
        rows = _query_history(
            client.network, client.station, client.location, channel_names,
            client.start_time, end_time,
        )
    except Exception as e:
        logging.error(f"SeedLink history query failed: {e}")
        return

    per_channel = defaultdict(lambda: {"start_time": None, "waveform": []})
    outbuf = bytearray()

    for channel, ts, waveform_json in rows:
        packet_time = datetime.fromtimestamp(ts, tz=timezone.utc)
        waveform = json.loads(waveform_json)
        buf = per_channel[channel]

        if buf["start_time"] is None:
            buf["start_time"] = packet_time

        buf["waveform"].extend(waveform)

        while len(buf["waveform"]) >= CHUNK_SIZE:
            chunk, buf["waveform"] = buf["waveform"][:CHUNK_SIZE], buf["waveform"][CHUNK_SIZE:]
            new_seq, data = _encode_seedlink_records(
                client.network, client.station, client.location, channel,
                client.sequence, buf["start_time"], SAMPLE_RATE, chunk,
            )
            client.sequence = new_seq
            outbuf += data
            buf["start_time"] += timedelta(seconds=CHUNK_SIZE / SAMPLE_RATE)

    for channel, buf in per_channel.items():
        if buf["waveform"]:
            new_seq, data = _encode_seedlink_records(
                client.network, client.station, client.location, channel,
                client.sequence, buf["start_time"], SAMPLE_RATE, buf["waveform"],
            )
            client.sequence = new_seq
            outbuf += data

    if outbuf:
        try:
            client.out_queue.put_nowait(bytes(outbuf))
        except asyncio.QueueFull:
            logging.warning(f"SeedLink client {client.client_id} too slow for history replay")


async def _flush_channel(channel_key: tuple) -> None:
    buffer = _CHANNEL_BUFFERS[channel_key]
    if not buffer["waveform"]:
        return

    network, code, location, channel = channel_key
    waveform = buffer["waveform"]
    start_time = buffer["start_time"]

    for client in list(_subscribers.values()):
        if not client.matches(network, code, location, channel):
            continue

        new_seq, data = _encode_seedlink_records(
            network, code, location, channel, client.sequence, start_time, SAMPLE_RATE, waveform,
        )
        client.sequence = new_seq

        try:
            client.out_queue.put_nowait(data)
        except asyncio.QueueFull:
            logging.warning(f"SeedLink client {client.client_id} too slow, dropping packet")

    _CHANNEL_BUFFERS[channel_key] = {"start_time": None, "waveform": []}


async def _process_incoming_packet(packet: dict) -> None:
    net = packet["station"]["network"]
    code = packet["station"]["code"]
    loc = packet["station"]["location"]
    chan = packet["station"]["channel"]
    channel_key = (net, code, loc, chan)

    packet_time = datetime.fromtimestamp(packet["timestamp"], tz=timezone.utc)
    waveform_chunk = packet["waveform"]

    buffer = _CHANNEL_BUFFERS[channel_key]

    if buffer["start_time"] is None:
        buffer["start_time"] = packet_time
    else:
        expected_next_time = buffer["start_time"] + timedelta(seconds=len(buffer["waveform"]) / SAMPLE_RATE)
        time_delta = abs((packet_time - expected_next_time).total_seconds())

        if time_delta > (0.5 / SAMPLE_RATE):
            await _flush_channel(channel_key)
            buffer = _CHANNEL_BUFFERS[channel_key]
            buffer["start_time"] = packet_time

    buffer["waveform"].extend(waveform_chunk)

    if len(buffer["waveform"]) >= CHUNK_SIZE:
        await _flush_channel(channel_key)


async def seedlink_worker() -> None:
    while True:
        packet = await seedlink_queue.get()

        try:
            await _process_incoming_packet(packet)
        except Exception as e:
            logging.error(f"SeedLink worker error: {e}", exc_info=True)
        finally:
            seedlink_queue.task_done()


def _cmd_hello(client: SeedLinkConnection, config: dict) -> None:
    org = config.get("organization", "")
    client.writer.write(f"{RELEASE}\r\n{org}\r\n".encode("ascii"))


def _cmd_station(client: SeedLinkConnection, args: list[str]) -> None:
    if len(args) < 2:
        client.writer.write(RES_ERR)
        return
    client.station = args[0][:5]
    client.network = args[1][:2]
    client.writer.write(RES_OK)


def _cmd_select(client: SeedLinkConnection, args: list[str]) -> None:
    if not args or not args[0]:
        client.writer.write(RES_ERR)
        return

    loc_chan = args[0]
    channel_type = None
    if "." in loc_chan:
        loc_chan, channel_type = loc_chan.split(".", 1)

    if len(loc_chan) == 3:
        client.location = "00"
        name = loc_chan
    elif len(loc_chan) == 5:
        client.location = loc_chan[:2]
        name = loc_chan[2:5]
    else:
        client.writer.write(RES_ERR)
        return

    client.channels.append((name, channel_type))
    client.writer.write(RES_OK)


def _cmd_data(client: SeedLinkConnection, args: list[str]) -> None:
    client.start_time = datetime.now(timezone.utc)
    if args:
        try:
            client.sequence = int(args[0], 16) + 1
        except ValueError:
            client.writer.write(RES_ERR)
            return
    client.writer.write(RES_OK)


def _parse_seedlink_time(value: str) -> datetime:
    year, month, day, hour, minute, second = (int(p) for p in value.split(","))
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _cmd_time(client: SeedLinkConnection, args: list[str]) -> None:
    ok = True

    if len(args) == 2:
        try:
            client.start_time = _parse_seedlink_time(args[0])
        except ValueError:
            ok = False
        try:
            client.end_time = _parse_seedlink_time(args[1])
        except ValueError:
            ok = False
    elif len(args) == 1:
        try:
            client.start_time = _parse_seedlink_time(args[0])
            client.end_time = datetime.now(timezone.utc)
        except ValueError:
            ok = False
    else:
        ok = False

    client.writer.write(RES_OK if ok else RES_ERR)


async def _cmd_info(client: SeedLinkConnection, args: list[str], config: dict) -> None:
    level = args[0].upper() if args else ""
    xml_bytes, channel_code = _build_info_xml(level, config)
    client.writer.write(_pack_info_response(xml_bytes, channel_code))


async def _cmd_end(client: SeedLinkConnection) -> None:
    if client.start_time is None:
        client.writer.write(RES_ERR)
        return

    client.streaming = True
    _subscribers[client.client_id] = client
    await _send_history(client)


async def _client_writer_loop(client: SeedLinkConnection) -> None:
    try:
        while True:
            data = await client.out_queue.get()
            client.writer.write(data)
            await client.writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass


async def _handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    client_id = f"{peer[0]}:{peer[1]}" if peer else str(id(writer))
    client = SeedLinkConnection(writer, client_id)
    config = get_config()

    writer_task = asyncio.create_task(_client_writer_loop(client))

    try:
        while True:
            try:
                raw = await reader.readuntil(b"\r")
            except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
                break

            line = raw.replace(b"\n", b"").rstrip(b"\r").decode("ascii", errors="replace").upper()
            if not line:
                continue
            if line == "BYE":
                break

            if client.streaming and line != "END" and "INFO " not in line:
                _subscribers.pop(client.client_id, None)
                client.streaming = False

            parts = line.split(" ")
            cmd = parts[0]
            args = [a for a in parts[1:] if a]

            if cmd == "HELLO":
                _cmd_hello(client, config)
            elif cmd in ("CAPABILITIES", "BATCH"):
                client.writer.write(RES_OK)
            elif cmd == "STATION":
                _cmd_station(client, args)
            elif cmd == "SELECT":
                _cmd_select(client, args)
            elif cmd == "DATA":
                _cmd_data(client, args)
            elif cmd == "TIME":
                _cmd_time(client, args)
            elif cmd == "INFO":
                await _cmd_info(client, args, config)
            elif cmd == "END":
                await _cmd_end(client)
            else:
                client.writer.write(RES_ERR)

            await client.writer.drain()
    except Exception as e:
        logging.debug(f"SeedLink connection {client_id} error: {e}")
    finally:
        _subscribers.pop(client.client_id, None)
        writer_task.cancel()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def handle_seedlink_server() -> None:
    config = get_config()
    address, port = config["seedlink_server"]["address"].split(":")
    port = int(port)

    try:
        server = await asyncio.start_server(_handle_connection, address, port)
        logging.info(f"Started SeedLink server on {address}:{port}")

        async with server:
            await server.serve_forever()

    except Exception as e:
        logging.error(f"Failed to run SeedLink listener: {e}")
