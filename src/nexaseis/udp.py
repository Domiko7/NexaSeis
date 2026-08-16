import socket
import struct
import logging
import asyncio

from nexaseis.common import get_config, decode_queue
from nexaseis.decoder import fmt, packet_size

import socket
import struct
import logging
import asyncio

def _handle_udp_clients(sock: socket.socket, size: int) -> None:
    try:
        while True:
            try:
                data = sock.recv(65535)
            except BlockingIOError:
                break

            if len(data) != size:
                continue

            try:
                decode_queue.put_nowait(data)
            except asyncio.QueueFull:
                pass

    except Exception as e:
        logging.error(f"UDP error: {e}")


async def handle_udp_listener() -> None:
    config = get_config()
    address, port = config["udp_listener"]["address"].split(":")
    port = int(port)
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            4 * 1024 * 1024
        )
        udp_socket.bind((address, port))
        udp_socket.setblocking(False)
        
        logging.info("Successfully started fast UDP listener")
        
        loop = asyncio.get_running_loop()
        loop.add_reader(udp_socket.fileno(), _handle_udp_clients, udp_socket, packet_size)

        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        logging.error(f"Failed to run UDP listener: {e}")