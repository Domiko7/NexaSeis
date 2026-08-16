import asyncio
import sqlite3
import importlib
import os

from nexaseis.utils.config import load_config

_cached_config = None

def get_config() -> dict:
    global _cached_config
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config

decode_queue = asyncio.Queue(maxsize=50000)
ws_queue = asyncio.Queue(maxsize=50000)
db_queue = asyncio.Queue(maxsize=50000)
datalink_queue = asyncio.Queue(maxsize=50000)
seedlink_queue = asyncio.Queue(maxsize=50000)

_config = get_config()
data_dir = _config.get("data_path", ".")
db_path = os.path.join(data_dir, "nexaseis.db")

stations = {}

os.makedirs(data_dir, exist_ok=True)

try:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
except Exception as e:
    print(f"Failed to connect to SQLite: {e}")
    conn = None