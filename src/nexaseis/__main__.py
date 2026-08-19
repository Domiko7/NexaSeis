import asyncio
import logging
import uvicorn
import os
import sys
from pathlib import Path

from nexaseis.udp import handle_udp_listener
from nexaseis.tcp import handle_tcp_listener
from nexaseis.services.ws import handle_ws_server, ws_worker
from nexaseis.services.datalink import datalink_worker
from nexaseis.db import init_db, db_worker
from nexaseis.station import load_stations
from nexaseis.common import get_config, conn
from nexaseis.decoder import decoder_worker
from nexaseis.utils.log import init_logging
from nexaseis.services.api_service import handle_api

async def main():
    init_logging()
    logging.info("Starting NexaSeis..")

    load_stations()
    init_db(conn)

    config = get_config()
    
    tasks = []

    tasks.append(asyncio.create_task(decoder_worker()))
    tasks.append(asyncio.create_task(ws_worker()))
    tasks.append(asyncio.create_task(db_worker()))
    tasks.append(asyncio.create_task(datalink_worker()))

    if config["ws_server"]["enabled"]:
        tasks.append(asyncio.create_task(handle_ws_server()))

    #if config["seedlink_server"]["enabled"]:
    #    tasks.append(asyncio.create_task(handle_seedlink_server()))

    if config["udp_listener"]["enabled"]:
        tasks.append(asyncio.create_task(handle_udp_listener()))

    if config["tcp_listener"]["enabled"]:
        tasks.append(asyncio.create_task(handle_tcp_listener()))

    if config["api"]["enabled"]:
        tasks.append(asyncio.create_task(handle_api()))

    await asyncio.gather(*tasks)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
