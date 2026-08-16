import numpy as np

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import numpy as np

from nexaseis.common import get_config, ws_queue, db_queue, datalink_queue, seedlink_queue

BUFFER_TARGET_SIZE = 70
SAMPLE_RATE = 100

_CHANNEL_BUFFERS = defaultdict(lambda: {"start_time": None, "waveform": []})


def process_packets(
    packet: dict, 
    time_array: list[float], 
    sensitivity: float
) -> dict:
    
    counts = np.asarray(packet["waveform"], dtype=float)
    time = np.asarray(time_array, dtype=float)

    demeaned_counts = counts - np.mean(counts)
    
    if not sensitivity:
        velocity = demeaned_counts
    else:
        velocity = demeaned_counts / sensitivity

    pgv = float(np.max(np.abs(velocity)))

    acceleration = np.gradient(velocity, time)
    pga = float(np.max(np.abs(acceleration)))

    displacement = np.zeros_like(velocity)
    for i in range(1, len(velocity)):
        displacement[i] = displacement[i - 1] + 0.5 * (velocity[i] + velocity[i - 1]) * (time[i] - time[i - 1])

    pgd = float(np.max(np.abs(displacement)))

    return {
        **packet,
        "pgv": pgv,
        "pga": pga,
        "pgd": pgd,
        "velocity": velocity.tolist(),
        "acceleration": acceleration.tolist(),
        "displacement": displacement.tolist()
    }