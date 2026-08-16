import logging
import os
import time
import numpy as np
import asyncio
from obspy import Trace, Stream, UTCDateTime

from nexaseis.db import get_or_create_station_id
from nexaseis.common import conn, stations
from nexaseis.utils.config import load_config

_config = load_config()
_data_dir = _config.get("data_path", ".")
images_dir = os.path.join(_data_dir, "images")


def refresh_helicorder(station: dict, type: str) -> str | None:
    current_time = time.time()
    
    net = station["network"]
    code = station["code"]
    loc = station["location"]
    chan = station["channel"]

    if type == "teleseismic":
        filename = f"helicorder_teleseismic_{net}_{code}_{loc}_{chan}.png"
    elif type == "standard":
        filename = f"helicorder_standard_{net}_{code}_{loc}_{chan}.png"
    else:
        filename = f"helicorder_raw_{net}_{code}_{loc}_{chan}.png"

    os.makedirs(images_dir, exist_ok=True)
    helicorder_path = os.path.join(images_dir, filename)

    cur = conn.cursor()
    station_id = get_or_create_station_id(cur, station)

    start_time_limit = current_time - 86400

    cur.execute("""
        SELECT timestamp, waveform 
        FROM waveform_packets 
        WHERE station_id = ? AND timestamp >= ?
        ORDER BY timestamp ASC;
    """, (station_id, start_time_limit))
    
    rows = cur.fetchall()
    if not rows:
        logging.warning(f"No waveform data found for station ID {station_id} in the last 24 hours.")
        return helicorder_path if os.path.exists(helicorder_path) else None

    stn_metadata = stations.get((net, code, loc), {})
    try:
        sps = stn_metadata["channels"][chan]["sample_rate"]
    except (KeyError, TypeError):
        sps = 100.0

    traces = [
        Trace(
            data=np.frombuffer(waveform_blob, dtype=np.float32),
            header={
                "network": net,
                "station": code,
                "channel": chan,
                "location": loc,
                "sampling_rate": sps,
                "starttime": UTCDateTime(pkt_timestamp)
            }
        )
        for pkt_timestamp, waveform_blob in rows
    ]

    st = Stream(traces=traces)
    st.merge(method=1, fill_value="latest")

    st_start = UTCDateTime(start_time_limit)
    st_end = UTCDateTime(current_time)
    st.trim(starttime=st_start, endtime=st_end, pad=True, fill_value=0)

    st.detrend("demean")
    st.detrend("linear")

    if type == "teleseismic":
        for tr in st:
            nyquist = tr.stats.sampling_rate / 2.0
            if nyquist > 1.2:
                tr.filter("lowpass", freq=0.8, corners=2, zerophase=True)
    elif type == "standard":
        for tr in st:
            nyquist = tr.stats.sampling_rate / 2.0
            if nyquist > 5.0:
                tr.filter("bandpass", freqmin=1.0, freqmax=5.0, corners=2, zerophase=True)

    st.plot(
        type="dayplot",
        interval=30,
        size=(2300, 1700),
        dpi=200,
        linewidth=0.7,
        right_vertical_labels=False,
        one_tick_per_line=True,
        show_y_UTC_label=True,
        events={"min_magnitude": 6.5},
        starttime=st_start,
        endtime=st_end,
        outfile=helicorder_path
    )

    logging.info(f"Helicorder updated successfully -> {helicorder_path}")

    return helicorder_path


def refresh_helicorders() -> None:
    for (net, code, loc), stn in stations.items():
        channels = stn.get("channels", {})
        for chan in channels.keys():
            station = {
                "network": net, 
                "code": code, 
                "location": loc, 
                "channel": chan
            }

            logging.info(f"Now proccessing the helicorder of {net}.{code}.{loc}")

            refresh_helicorder(station, "standard")
            refresh_helicorder(station, "raw")
            refresh_helicorder(station, "teleseismic")


async def helicorder_worker() -> None:
    while True:
        try:
            await asyncio.to_thread(refresh_helicorders)
        except Exception as e:
            logging.error(f"Error in helicorder worker: {e}")

        await asyncio.sleep(500)
