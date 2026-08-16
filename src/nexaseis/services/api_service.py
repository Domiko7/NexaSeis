import uvicorn
import asyncio
from nexaseis.common import load_config

from nexaseis.uvicorn import app
from nexaseis.utils.helicorder import helicorder_worker

async def handle_api() -> None:
    tasks = []

    config = load_config()
    server_address = config.get("api", {}).get("address", "0.0.0.0:8000")

    host, port = server_address.split(":")
    uvicorn_config = uvicorn.Config(
        app, host=host, port=int(port), log_level="info", loop="asyncio"
    )
    server = uvicorn.Server(uvicorn_config)
    tasks.append(asyncio.create_task(server.serve()))

    tasks.append(asyncio.create_task(helicorder_worker()))

    await asyncio.gather(*tasks)