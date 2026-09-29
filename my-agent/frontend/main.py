from dotenv import load_dotenv
load_dotenv()
"""
FloraGuide FastAPI Web & API Application.
Serves the multi-view application (Today, My Garden, Journal, Plans, Assistant)
with local ADK runner fallback and optional remote Agent Engine / A2A proxying.
"""

import os
import uuid
import sys

# Ensure my-agent root is on path for app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import gardening_store as store
from app import gardening_tools as tools
from app.weather_adapter import WeatherAdapter
from app.agent import app as adk_app, root_agent

app = FastAPI(title="FloraGuide")

# --- In-Memory Session State for Local Chat ---
_conversations: dict[str, list] = {}

class ChatRequest(BaseModel):
    message: str
    sessionId: str | None = None

class ObsRequest(BaseModel):
    notes: str
    plant_id: str | None = None
    category: str = "general"

class AreaRequest(BaseModel):
    name: str
    area_type: str = "patio"
    sun_exposure: str = "full sun"
    shelter_from_rain: bool = False
    watering_arrangements: str = ""
    area_id: str | None = None
    notes: str = ""
    surface_material: str = ""

class PlantRequest(BaseModel):
    area_id: str
    name: str
    species: str | None = None
    planting_type: str = "container"
    container_size_liters: float | None = None
    substrate_type: str | None = None
    drainage_quality: str = "good"
    plant_id: str | None = None

class QuickCareRequest(BaseModel):
    action: str  # "water", "observe", "photo"
    notes: str = ""
    photo_url: str | None = None
    category: str = "general"

class MoveAreaRequest(BaseModel):
    area_id: str | None = ""

class LayoutRequest(BaseModel):
    layout: dict

class TravelRequest(BaseModel):
    departure_date: str
    return_date: str
    available_help: str = "none"

# --- REST Endpoints for Views ---
@app.get("/api/garden")
async def api_garden(garden_id: str | None = None):
    target = store.get_garden(garden_id) if garden_id else store.get_active_garden()
    if not target:
        store.create_or_reset_example_garden(switch_to=True)
        target = store.get_active_garden()
    else:
        # Check if empty garden (0 areas or 0 plants), auto-seed example garden immediately
        areas = store.list_growing_areas(target["id"])
        area_ids = {a["id"] for a in areas}
        plants = [p for p in store.list_plants() if p.get("area_id") in area_ids]
        if len(areas) == 0 or len(plants) == 0:
            store.create_or_reset_example_garden(switch_to=True)
            target = store.get_active_garden()
    return tools.get_garden_summary(target["id"])

@app.post("/api/garden/load-example")
async def api_load_example_garden():
    res = store.create_or_reset_example_garden(garden_id="example-garden", switch_to=True)
    summary = tools.get_garden_summary("example-garden")
    layout = store.get_garden_layout("example-garden")
    return {
        "status": "success",
        "message": "FloraGuide Demonstration Garden loaded successfully.",
        "garden": summary["garden"],
        "growing_areas": summary["growing_areas"],
        "plants": summary["plants"],
        "layout": layout
    }

@app.get("/api/gardens")
async def api_list_gardens():
    gardens = store.list_gardens()
    for g in gardens:
        summary = tools.get_garden_summary(g["id"])
        g["total_plants"] = len(summary.get("plants", []))
    active = store.get_active_garden()
    active_id = active["id"] if active else (gardens[0]["id"] if gardens else "example-garden")
    return {"gardens": gardens, "active_garden_id": active_id}

@app.post("/api/gardens/switch/{garden_id}")
async def api_switch_garden(garden_id: str):
    g = store.set_active_garden(garden_id)
    if not g:
        return JSONResponse(status_code=404, content={"error": f"Garden {garden_id} not found"})
    summary = tools.get_garden_summary(garden_id)
    layout = store.get_garden_layout(garden_id)
    return {
        "status": "success",
        "garden": g,
        "growing_areas": summary["growing_areas"],
        "plants": summary["plants"],
        "layout": layout
    }

@app.get("/api/weather")
async def api_weather():
    return tools.check_local_weather()

@app.get("/api/tasks")
async def api_tasks():
    return {"tasks": store.list_tasks()}

@app.post("/api/tasks/{task_id}/complete")
async def api_complete_task(task_id: str):
    task = store.update_task_status(task_id, "completed")
    if not task:
        return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})
    return {"status": "success", "task": task}

@app.post("/api/plan/generate")
async def api_generate_plan():
    return tools.generate_conditional_care_plan()

@app.get("/api/journal")
async def api_journal():
    return {"entries": store.list_journal_entries(limit=50)}

@app.post("/api/journal")
async def api_add_journal(req: ObsRequest):
    return tools.record_plant_observation(notes=req.notes, plant_id=req.plant_id, category=req.category)

@app.post("/api/areas")
async def api_add_area(req: AreaRequest):
    return tools.add_or_update_growing_area(
        name=req.name,
        area_type=req.area_type,
        sun_exposure=req.sun_exposure,
        shelter_from_rain=req.shelter_from_rain,
        watering_arrangements=req.watering_arrangements,
        area_id=req.area_id,
        notes=req.notes
    )

@app.delete("/api/areas/{area_id}")
async def api_delete_area(area_id: str, retain_plants: bool = True):
    store.delete_growing_area(area_id, retain_plants=retain_plants)
    return {"status": "success", "deleted_area_id": area_id}

@app.post("/api/plants")
async def api_add_plant(req: PlantRequest):
    res = tools.add_or_update_plant(
        area_id=req.area_id,
        name=req.name,
        species=req.species,
        planting_type=req.planting_type,
        container_size_liters=req.container_size_liters,
        substrate_type=req.substrate_type,
        drainage_quality=req.drainage_quality,
        plant_id=req.plant_id
    )
    if res.get("plant"):
        res["plant"]["condition"] = store.evaluate_plant_condition(res["plant"]["id"])
    return res

@app.post("/api/plants/{plant_id}/area")
async def api_move_plant(plant_id: str, req: MoveAreaRequest):
    res = store.update_plant_area(plant_id, req.area_id or "")
    if res:
        res["condition"] = store.evaluate_plant_condition(plant_id)
        return {"status": "success", "plant": res}
    return JSONResponse(status_code=404, content={"error": f"Plant {plant_id} not found"})

@app.post("/api/plants/{plant_id}/quick-care")
async def api_plant_quick_care(plant_id: str, req: QuickCareRequest):
    if req.action == "water":
        notes = req.notes or "Watered thoroughly until slight drainage."
        res = tools.record_plant_watering(plant_id, notes=notes)
        return res
    elif req.action == "observe":
        notes = req.notes or "Observation recorded."
        res = tools.record_plant_observation(notes=notes, plant_id=plant_id, category=req.category, photo_url=req.photo_url)
        condition = store.evaluate_plant_condition(plant_id)
        return {"status": "success", "journal_entry": res.get("journal_entry"), "condition": condition}
    elif req.action == "photo":
        res = tools.record_plant_observation(notes=req.notes or "New photo updated", plant_id=plant_id, category="general", photo_url=req.photo_url)
        condition = store.evaluate_plant_condition(plant_id)
        return {"status": "success", "journal_entry": res.get("journal_entry"), "condition": condition}
    return JSONResponse(status_code=400, content={"error": f"Unknown action: {req.action}"})

@app.delete("/api/plants/{plant_id}")
async def api_delete_plant(plant_id: str):
    store.delete_plant(plant_id)
    return {"status": "success", "deleted_plant_id": plant_id}

@app.get("/api/garden/layout")
async def api_get_layout(garden_id: str | None = None):
    garden = store.get_garden(garden_id) if garden_id else store.get_active_garden()
    gid = garden["id"] if garden else "default-garden"
    layout = store.get_garden_layout(gid)
    return {"layout": layout}

@app.post("/api/garden/layout")
async def api_save_layout(req: LayoutRequest, garden_id: str | None = None):
    garden = store.get_garden(garden_id) if garden_id else store.get_active_garden()
    gid = garden["id"] if garden else "default-garden"
    res = store.save_garden_layout(gid, req.layout)
    return res

@app.post("/api/travel/plan")
async def api_plan_travel(req: TravelRequest):
    return tools.plan_travel_absence(
        departure_date=req.departure_date,
        return_date=req.return_date,
        available_help=req.available_help
    )

# --- A2A Proxy & Chat Endpoint (build-agent-frontend pattern) ---
import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
from app.app_utils import services

RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "")
if not RESOURCE:
    meta_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    if os.path.exists(meta_path):
        import json
        try:
            with open(meta_path) as f:
                RESOURCE = json.load(f).get("remote_agent_runtime_id", "")
        except Exception:
            pass

AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0] if "/locations/" in RESOURCE else "us-central1"

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"
_A2UI_MIME = "application/json+a2ui"

try:
    _creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
except Exception:
    _creds = None


def _auth_headers() -> dict[str, str]:
    if _creds:
        _creds.refresh(google.auth.transport.requests.Request())
        return {
            "Authorization": f"Bearer {_creds.token}",
            "Content-Type": "application/json",
        }
    return {"Content-Type": "application/json"}


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            data = data[0]
        card = AgentCard(**data)
        card.url = A2A_BASE
        _card = card
    return _card


import json

def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI.
    Text parts pass through as {"kind": "text"}. A2UI data parts become
    {"kind": "a2ui", "data": ...} so the UI renders them as cards.
    Also extracts any <a2ui-json>...</a2ui-json> embedded blocks into a2ui parts.
    """
    out: list[dict] = []

    def _process_text(text_val: str):
        if "<a2ui-json>" in text_val and "</a2ui-json>" in text_val:
            before = text_val.split("<a2ui-json>")[0].strip()
            middle = text_val.split("<a2ui-json>")[1].split("</a2ui-json>")[0].strip()
            after = text_val.split("</a2ui-json>")[1].strip()
            if before:
                out.append({"kind": "text", "text": before})
            try:
                parsed = json.loads(middle)
                out.append({"kind": "a2ui", "data": parsed})
            except Exception:
                out.append({"kind": "text", "text": middle})
            if after:
                _process_text(after)
        else:
            if text_val:
                out.append({"kind": "text", "text": text_val})

    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            _process_text(root.text)
        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": root.data})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
        elif isinstance(root, dict):
            if root.get("text"):
                _process_text(root["text"])
            elif root.get("data"):
                meta = root.get("metadata") or {}
                if meta.get("mimeType") == _A2UI_MIME:
                    out.append({"kind": "a2ui", "data": root["data"]})
    return out


# Local fallback runner
_session_service = InMemorySessionService()
_artifact_service = InMemoryArtifactService()
_runner = Runner(
    app=adk_app,
    session_service=_session_service,
    artifact_service=_artifact_service,
    memory_service=services.get_memory_service(),
    auto_create_session=True,
)


async def _local_chat_fallback(message: str, user_id: str) -> JSONResponse:
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    )
    reply_texts = []
    try:
        events = _runner.run_async(
            session_id=user_id,
            user_id="default-user",
            new_message=content,
        )
        async for event in events:
            if hasattr(event, "content") and event.content:
                for part in event.content.parts or []:
                    if getattr(part, "text", None):
                        reply_texts.append(part.text)
        full_reply = "\n\n".join(reply_texts) if reply_texts else "(FloraGuide completed the analysis.)"
        return JSONResponse({"parts": [{"kind": "text", "text": full_reply}], "sessionId": user_id})
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={"parts": [{"kind": "text", "text": f"Error: {e}"}], "sessionId": user_id},
        )


@app.post("/chat")
async def chat_handler(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    message = body.get("message", "")
    user_id = body.get("user_id") or body.get("sessionId") or "web-user"
    parts: list[dict] = []

    if RESOURCE:
        try:
            async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
                card = await _get_card(client)
                factory = ClientFactory(
                    ClientConfig(
                        supported_transports=[
                            TransportProtocol.jsonrpc,
                            TransportProtocol.http_json,
                        ],
                        httpx_client=client,
                    )
                )
                a2a_client = factory.create(card)

                msg = Message(
                    message_id=str(uuid.uuid4()),
                    role=Role.user,
                    parts=[Part(root=TextPart(text=message))],
                    context_id=_contexts.get(user_id),
                )

                last_task = None
                got_artifact_update = False
                async for event in a2a_client.send_message(msg):
                    if not isinstance(event, tuple):
                        continue
                    task, update = event
                    if task is not None:
                        last_task = task
                        if getattr(task, "context_id", None):
                            _contexts[user_id] = task.context_id
                    if isinstance(update, TaskArtifactUpdateEvent):
                        got_artifact_update = True
                        for p in _extract_parts(update.artifact.parts):
                            if p not in parts:
                                parts.append(p)
                    elif hasattr(update, "status") and getattr(update.status, "message", None):
                        status_msg = update.status.message
                        if getattr(status_msg, "role", None) in (Role.agent, "agent"):
                            for p in _extract_parts(getattr(status_msg, "parts", None) or []):
                                if p not in parts:
                                    parts.append(p)

                # Non-streaming fallback: pull parts from artifacts or history
                if not got_artifact_update and last_task is not None:
                    for artifact in getattr(last_task, "artifacts", None) or []:
                        for p in _extract_parts(artifact.parts):
                            if p not in parts:
                                parts.append(p)
                    if not parts:
                        for hist_msg in getattr(last_task, "history", None) or []:
                            if getattr(hist_msg, "role", None) in (Role.agent, "agent"):
                                for p in _extract_parts(getattr(hist_msg, "parts", None) or []):
                                    if p not in parts:
                                        parts.append(p)
                    if not parts and getattr(getattr(last_task, "status", None), "message", None):
                        status_msg = last_task.status.message
                        if getattr(status_msg, "role", None) in (Role.agent, "agent"):
                            for p in _extract_parts(getattr(status_msg, "parts", None) or []):
                                if p not in parts:
                                    parts.append(p)
        except Exception as e:
            print(f"[Remote A2A Proxy Notice] {e}. Falling back to local ADK runner.")
            return await _local_chat_fallback(message, user_id)
    else:
        return await _local_chat_fallback(message, user_id)

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts, "sessionId": user_id})


# Serve UI static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
