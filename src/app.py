"""FastAPI Web Application & Live Telemetry WebSocket Server.

Exposes REST APIs and a WebSocket stream for real-time memory monitoring,
process management, and time-series charting.
"""

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.monitor import MemoryMonitor

# Initialize core monitor
monitor = MemoryMonitor(max_history_points=60)
background_recording_task: Optional[asyncio.Task] = None


async def memory_history_recorder():
    """Background worker to continuously record memory snapshots for live charts."""
    while True:
        try:
            monitor.record_history_snapshot()
            await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown routines."""
    global background_recording_task
    # Start background memory recorder
    background_recording_task = asyncio.create_task(memory_history_recorder())
    yield
    # Clean up on shutdown
    if background_recording_task:
        background_recording_task.cancel()
        try:
            await background_recording_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Memory Dashboard & Process Monitor",
    description="Real-time Windows & Cross-Platform System Memory & Process Telemetry",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Serve the single-page web dashboard."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"error": "Dashboard UI not yet created."}
    return FileResponse(index_file)


@app.get("/api/system")
async def get_system_summary():
    """Return current physical and swap memory metrics and machine info."""
    return monitor.get_system_summary()


@app.get("/api/processes")
async def get_processes(
    grouped: bool = Query(default=False, description="Group instances by application"),
    sort_by: str = Query(default="rss", description="Sort field: rss, percent, cpu, name, pid, instances"),
    sort_order: str = Query(default="desc", description="Sort direction: asc or desc"),
    search: str = Query(default="", description="Filter by process name, PID, user, category"),
    min_mb: float = Query(default=0.0, description="Minimum RSS memory in MB"),
    limit: Optional[int] = Query(default=None, description="Max number of items to return"),
):
    """Retrieve filtered, sorted, and optionally grouped process list."""
    procs = monitor.get_processes(
        grouped=grouped,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        min_mb=min_mb,
        limit=limit,
    )
    return {
        "count": len(procs),
        "grouped": grouped,
        "processes": procs,
    }


@app.get("/api/processes/{pid}")
async def get_process_details(pid: int):
    """Retrieve detailed metadata for a single process."""
    details = monitor.get_process_details(pid)
    if not details:
        raise HTTPException(status_code=404, detail=f"Process with PID {pid} not found or inaccessible.")
    return details


class KillRequest(BaseModel):
    force: bool = False


@app.post("/api/processes/{pid}/kill")
async def kill_process(pid: int, req: KillRequest = KillRequest()):
    """Terminate or kill a process by PID with safety checks."""
    result = monitor.terminate_process(pid, force=req.force)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to terminate process."))
    return result


@app.get("/api/history")
async def get_memory_history():
    """Return rolling time-series memory usage history."""
    return {"history": monitor.get_history()}


@app.get("/api/recommendations")
async def get_recommendations():
    """Return high-level memory analysis and optimization tips."""
    return monitor.get_recommendations()


@app.websocket("/ws/live")
async def websocket_live_stream(websocket: WebSocket):
    """WebSocket endpoint for live, bi-directional memory telemetry."""
    await websocket.accept()
    interval = 2.0
    paused = False

    async def receiver():
        nonlocal interval, paused
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    payload = json.loads(msg_text)
                    action = payload.get("action")
                    if action == "set_interval":
                        new_val = float(payload.get("interval", 2.0))
                        interval = max(0.5, min(10.0, new_val))
                    elif action == "pause":
                        paused = True
                    elif action == "resume":
                        paused = False
                except Exception:
                    pass
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    receiver_task = asyncio.create_task(receiver())

    try:
        while True:
            if not paused:
                summary = monitor.get_system_summary()
                history = monitor.get_history()
                top_apps = monitor.get_processes(grouped=True, sort_by="rss", sort_order="desc", limit=8)
                payload = {
                    "type": "telemetry",
                    "summary": summary,
                    "history": history,
                    "top_apps": top_apps,
                }
                await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(interval)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        receiver_task.cancel()
        try:
            await receiver_task
        except asyncio.CancelledError:
            pass
