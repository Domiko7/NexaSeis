import asyncio
import json
import logging

from websockets.asyncio.server import ServerConnection, serve
from collections.abc import Awaitable
from nexaseis.common import get_config, ws_queue

_clients = set()

async def _handle_ws_message(websocket: ServerConnection) -> Awaitable[None]:
    _clients.add(websocket)
    try:
        async for message in websocket:
            await websocket.send(message)
    finally:
        _clients.remove(websocket)

async def _broadcast_ws_message(data: dict) -> None:
    if not _clients:
        return

    message = json.dumps(data)

    tasks = [client.send(message) for client in _clients]

    await asyncio.gather(*tasks, return_exceptions=True)

async def ws_worker():
    while True:
        packet = await ws_queue.get()

        try:
            await _broadcast_ws_message(packet)
        except Exception as e:
            logging.error(f"WS error: {e}")
        finally:
            ws_queue.task_done()

async def handle_ws_server() -> None:
    config = get_config()
    address, port = config["ws_server"]["address"].split(":")
    port = int(port)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    async with serve(_handle_ws_message, address, port) as server:
        await server.serve_forever()