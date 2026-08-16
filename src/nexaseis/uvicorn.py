import os
import time
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from typing import Literal

from nexaseis.common import load_config
from nexaseis.utils.helicorder import refresh_helicorder, images_dir

_config = load_config()

app = FastAPI(title="NexaSeis API", version="1.0")

if _config["api"]["cors"]:
    origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
async def root():
    return {
        "status": "running",
        "server_time": time.time()
    }

stations_api = {}

@app.get("/stations")
async def get_station_data():
    return stations_api


from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
import os

@app.get("/helicorder/{network}/{code}/{location}/{channel}")
async def get_helicorder(
    network: str, 
    code: str, 
    location: str, 
    channel: str, 
    background_tasks: BackgroundTasks,
    type: Literal["standard", "teleseismic", "raw"] = "standard"
):
    station = {
        "network": network, 
        "code": code, 
        "location": location, 
        "channel": channel
    }
    
    if type == "teleseismic":
        filename = f"helicorder_teleseismic_{network}_{code}_{location}_{channel}.png"
    elif type == "standard":
        filename = f"helicorder_standard_{network}_{code}_{location}_{channel}.png"
    else:
        filename = f"helicorder_raw_{network}_{code}_{location}_{channel}.png"
        
    helicorder_path = os.path.join(images_dir, filename)


    if os.path.exists(helicorder_path):
        return FileResponse(
            helicorder_path, 
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=100"}
        )

    raise HTTPException(
        status_code=202, 
        detail="404 not found"
    )