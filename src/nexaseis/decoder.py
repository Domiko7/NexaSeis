import struct
import logging

from nexaseis.common import decode_queue
from nexaseis.station import handle_station

fmt = "<d 8s 8s 8s 8s 5i"
packet_size = struct.calcsize(fmt)

def _decode_packet(data) -> dict:
    unpacked = struct.unpack(fmt, data)

    packet = {
        "timestamp": unpacked[0],
        "station": {
            "code": unpacked[1].decode("ascii", errors="replace").strip("\x00"),
            "network": unpacked[2].decode("ascii", errors="replace").strip("\x00"),
            "channel": unpacked[3].decode("ascii", errors="replace").strip("\x00"),
            "location": unpacked[4].decode("ascii", errors="replace").strip("\x00"),
        },
        "waveform": list(unpacked[5:])
    }

    return packet

async def decoder_worker() -> None:
    while True:
        data = await decode_queue.get()

        try:
            packet = _decode_packet(data)
            await handle_station(packet)
        except Exception as e:
            logging.error(f"Decode error: {e}")
        finally:
            decode_queue.task_done() 