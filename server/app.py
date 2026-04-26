import json
import os

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
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

from fastapi import Request, WebSocket
from fastapi.staticfiles import StaticFiles
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Client connected. Total: {len(self.active_connections)}", flush=True)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS] Client disconnected. Total: {len(self.active_connections)}", flush=True)

    async def broadcast(self, message: str):
        dead = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for c in dead:
            self.disconnect(c)
        print(f"[WS] Broadcast to {len(self.active_connections)} connections, {len(dead)} dead removed", flush=True)


manager = ConnectionManager()


def _build_live_payload(env_instance) -> dict:
    incidents = []
    try:
        task_spec = env_instance._task_spec
        runtime = env_instance._tickets_runtime
        for ticket in task_spec.tickets:
            rt = runtime.get(ticket.ticket_id, {})
            incidents.append({
                "id": ticket.ticket_id,
                "message": ticket.customer_message,
                "priority": rt.get("predicted_priority") or ticket.gold_priority,
                "lat": ticket.lat,
                "lon": ticket.lon,
                "submitted": rt.get("submitted", False),
                "team": rt.get("predicted_team"),
                "score": rt.get("ticket_score", 0.0),
            })
        score = env_instance._state.cumulative_reward
        budget_used = sum(
            env_instance._estimate_resource_cost(runtime.get(t.ticket_id, {}))
            for t in task_spec.tickets
            if runtime.get(t.ticket_id, {}).get("submitted")
        )
        resources = max(0, 100 - budget_used * 4)
    except Exception:
        score = 0.0
        resources = 100

    return {
        "score": round(score, 4),
        "resources": resources,
        "incidents": incidents,
    }


@app.middleware("http")
async def disable_ui_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/ui"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.websocket("/dashboard-ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_text('{"type":"connected"}')
    except Exception:
        manager.disconnect(websocket)
        return
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=25.0)
                if data == "ping":
                    await websocket.send_text('{"type":"pong"}')
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text('{"type":"ping"}')
                except Exception:
                    break
    except Exception:
        pass
    finally:
        manager.disconnect(websocket)


@app.post("/ui/update")
async def post_ui_update(data: dict):
    print(f"[UI] /ui/update called, broadcasting to {len(manager.active_connections)} connections", flush=True)
    await manager.broadcast(json.dumps({"type": "update", "payload": data}))
    return {"status": "ok"}


@app.middleware("http")
async def broadcast_after_step(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/step" and response.status_code == 200:
        try:
            env_registry = getattr(app.state, "env_registry", None)
            if env_registry:
                envs = list(env_registry.values()) if hasattr(env_registry, "values") else []
                if envs:
                    payload = _build_live_payload(envs[0])
                    asyncio.create_task(
                        manager.broadcast(json.dumps({"type": "update", "payload": payload}))
                    )
        except Exception:
            pass
    return response


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
            incidents.append({
                "id": ticket.ticket_id,
                "message": ticket.customer_message,
                "priority": ticket.gold_priority,
                "lat": ticket.lat,
                "lon": ticket.lon,
                "submitted": False,
                "team": None,
                "score": 0.0,
            })

    return {
        "task": task,
        "score": 0.0,
        "resources": 100,
        "incidents": incidents,
    }


from fastapi import BackgroundTasks

async def simulate_demo_run(task_name: str):
    """Simulates a perfect agent run to show off the dashboard."""
    # This imports internally to avoid circular deps or startup issues
    try:
        from .support_ops_environment import SupportOpsEnvironment
        from ..tasks import TASKS
        from ..models import SupportOpsAction
    except ImportError:
        from server.support_ops_environment import SupportOpsEnvironment
        from tasks import TASKS
        from models import SupportOpsAction

    env = SupportOpsEnvironment(task_name=task_name)
    # We need to find the session in the app state to update the live payload
    # For demo purposes, we'll just broadcast updates directly using the manager
    
    task_spec = TASKS.get(task_name, TASKS["easy"])
    
    await manager.broadcast(json.dumps({
        "type": "update", 
        "payload": {
            "score": 0.0,
            "resources": 100,
            "incidents": [_build_live_payload(env)["incidents"][0]] # Start state
        }
    }))
    
    for ticket in task_spec.tickets:
        tid = ticket.ticket_id
        
        # 1. Classify
        await asyncio.sleep(0.8)
        env.step(SupportOpsAction(action_type="classify", ticket_id=tid, predicted_team=ticket.gold_team))
        await manager.broadcast(json.dumps({"type": "update", "payload": _build_live_payload(env)}))
        
        # 2. Set Priority
        await asyncio.sleep(0.6)
        env.step(SupportOpsAction(action_type="set_priority", ticket_id=tid, predicted_priority=ticket.gold_priority))
        await manager.broadcast(json.dumps({"type": "update", "payload": _build_live_payload(env)}))
        
        # 3. Draft
        await asyncio.sleep(0.7)
        env.step(SupportOpsAction(action_type="draft_reply", ticket_id=tid, reply_text=f"Deploying {ticket.gold_team} team to coordinates. ETA 15 mins. Triage initiated."))
        await manager.broadcast(json.dumps({"type": "update", "payload": _build_live_payload(env)}))
        
        # 4. Submit
        await asyncio.sleep(1.0)
        env.step(SupportOpsAction(action_type="submit_ticket", ticket_id=tid))
        await manager.broadcast(json.dumps({"type": "update", "payload": _build_live_payload(env)}))

    await manager.broadcast(json.dumps({"type": "update", "payload": _build_live_payload(env)}))


@app.post("/ui/run-demo")
async def run_demo(background_tasks: BackgroundTasks, task: str = "easy"):
    print(f"[UI] Demo requested for task: {task}", flush=True)
    background_tasks.add_task(simulate_demo_run, task)
    return {"status": "demo_started"}


app.mount(
    "/ui",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "ui"), html=True),
    name="ui",
)


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()