import importlib
import logging
import asyncio
import numpy as np

from nexaseis.common import get_config, db_queue, conn

_config = get_config()
packet_count = 0

STATION_CACHE = {}


def init_db(conn):
    cur = conn.cursor()
    
    cur.execute("PRAGMA journal_mode = WAL;")
    cur.execute("PRAGMA synchronous = NORMAL;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network TEXT NOT NULL,
            code TEXT NOT NULL,
            channel TEXT NOT NULL,
            location TEXT NOT NULL,
            UNIQUE (network, code, channel, location)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS waveform_packets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DOUBLE PRECISION NOT NULL,
            station_id INT REFERENCES stations(id),
            waveform BLOB
        );
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_waveform_station_time 
        ON waveform_packets (station_id, timestamp ASC);
    """)

    conn.commit()


def get_or_create_station_id(cur, station: dict) -> int:
    cache_key = (station["network"], station["code"], station["channel"], station["location"])
    
    if cache_key in STATION_CACHE:
        return STATION_CACHE[cache_key]

    cur.execute("""
        INSERT INTO stations (network, code, channel, location)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (network, code, channel, location)
        DO UPDATE SET network = excluded.network;
    """, cache_key)
    
    cur.execute("""
        SELECT id FROM stations
        WHERE network = ? AND code = ? AND channel = ? AND location = ?;
    """, cache_key)
    
    station_id = cur.fetchone()[0]
    STATION_CACHE[cache_key] = station_id
    return station_id


def insert_packets_batch(conn, packets: list[dict]) -> None:
    global packet_count
    if not packets:
        return

    cur = conn.cursor()
    waveform_data = []

    for packet in packets:
        station_id = get_or_create_station_id(cur, packet["station"])
        
        raw_waveform = packet["waveform"]
        if not isinstance(raw_waveform, np.ndarray):
            raw_waveform = np.array(raw_waveform, dtype=np.float32)
        else:
            raw_waveform = raw_waveform.astype(np.float32, copy=False)

        waveform_data.append((
            packet["timestamp"],
            station_id,
            raw_waveform.tobytes()
        ))

    cur.executemany("""
        INSERT INTO waveform_packets (timestamp, station_id, waveform)
        VALUES (?, ?, ?)
    """, waveform_data)

    conn.commit()

    packet_count += len(packets)
    if packet_count >= 1000:
        logging.info(f"Successfully saved {packet_count} packets.")
        packet_count = 0


async def db_worker() -> None:
    BATCH_SIZE = 100
    
    while True:
        packets_to_process = []
        
        first_packet = await db_queue.get()
        packets_to_process.append(first_packet)

        while len(packets_to_process) < BATCH_SIZE and not db_queue.empty():
            try:
                packet = db_queue.get_nowait()
                packets_to_process.append(packet)
            except asyncio.QueueEmpty:
                break

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, insert_packets_batch, conn, packets_to_process)

        except Exception as e:
            logging.error(f"Database error during batch insert: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        finally:
            for _ in range(len(packets_to_process)):
                db_queue.task_done()