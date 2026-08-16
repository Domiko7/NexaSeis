import struct
import logging
import asyncio

from nexaseis.common import get_config, decode_queue
from nexaseis.decoder import fmt, packet_size

async def _handle_tcp_clients(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        while True:
            data = await reader.readexactly(packet_size)

            try:
                decode_queue.put_nowait(data)
            except asyncio.QueueFull:
                pass

    except Exception:
        pass
    finally:
        writer.close()
        await writer.wait_closed()

async def handle_tcp_listener() -> None:
    config = get_config()
    address, port = config["tcp_listener"]["address"].split(":")
    port = int(port)
    
    try:
        server = await asyncio.start_server(_handle_tcp_clients, address, port)
        
        logging.info(f"Successfully started TCP listener")
        
        async with server:
            await server.serve_forever()
            
    except Exception as e:
        logging.error(f"Failed to run TCP listener: {e}")