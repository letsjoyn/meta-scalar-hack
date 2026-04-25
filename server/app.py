import json
import os

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required. Install dependencies with: pip install -e ."
    ) from e


os.environ.setdefault("ENABLE_WEB_INTERFACE", "true")

try:
    from ..models import SupportOpsAction, SupportOpsObservation
    from .support_ops_environment import SupportOpsEnvironment
    from ..tasks import TASKS
except ImportError:
    from models import SupportOpsAction, SupportOpsObservation
    from server.support_ops_environment import SupportOpsEnvironment
    from tasks import TASKS


app = create_app(
    SupportOpsEnvironment,
    SupportOpsAction,
    SupportOpsObservation,
    env_name="support_ops_env",
    max_concurrent_envs=2,
)

# ── Websocket and UI ─────────────────────────────────────────────────────

from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()


@app.middleware("http")
async def disable_ui_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/ui"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We are just broadcasting, so we don't need to receive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# This will be used by the agent to push updates
@app.post("/ui/update")
async def post_ui_update(data: dict):
    await manager.broadcast(json.dumps({"type": "update", "payload": data}))
    return {"status": "ok"}


@app.get("/ui/bootstrap")
async def ui_bootstrap(task: str = "all"):
    incidents = []

    task_specs = []
    if task == "all":
        task_specs = list(TASKS.values())
    elif task in TASKS:
        task_specs = [TASKS[task]]
    else:
        task_specs = [TASKS["easy"]]

    for spec in task_specs:
        for ticket in spec.tickets:
            incidents.append(
                {
                    "id": ticket.ticket_id,
                    "message": ticket.customer_message,
                    "priority": ticket.gold_priority,
                    "lat": ticket.lat,
                    "lon": ticket.lon,
                    "submitted": False,
                }
            )

    return {
        "task": task,
        "score": 0.0,
        "resources": 100,
        "incidents": incidents,
    }

# Mount the static files for the UI
app.mount(
    "/ui",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "ui"), html=True),
    name="ui",
)

# ── Main ─────────────────────────────────────────────────────────────────


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
