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
    area_type: str
    sun_exposure: str
    shelter_from_rain: bool
    watering_arrangements: str = ""
    area_id: str | None = None

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
    area_id: str

class LayoutRequest(BaseModel):
    layout: dict

class TravelRequest(BaseModel):
    departure_date: str
    return_date: str
    available_help: str = "none"

# --- REST Endpoints for Views ---
@app.get("/api/garden")
async def api_garden():
    return tools.get_garden_summary()

@app.get("/api/weather")
async def api_weather():
    return tools.check_local_weather()

@app.get("/api/tasks")
async def api_tasks():
    return {"tasks": store.list_tasks()}

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
        area_id=req.area_id
    )

@app.delete("/api/areas/{area_id}")
async def api_delete_area(area_id: str):
    store.delete_growing_area(area_id)
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
    res = store.update_plant_area(plant_id, req.area_id)
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
async def api_get_layout():
    garden = store.get_default_garden()
    gid = garden["id"] if garden else "default-garden"
    layout = store.get_garden_layout(gid)
    return {"layout": layout}

@app.post("/api/garden/layout")
async def api_save_layout(req: LayoutRequest):
    garden = store.get_default_garden()
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

# --- Chat Endpoint (ADK Runner invocation) ---
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
from app.app_utils import services

_session_service = InMemorySessionService()
_artifact_service = InMemoryArtifactService()
_runner = Runner(
    app=adk_app,
    session_service=_session_service,
    artifact_service=_artifact_service,
    memory_service=services.get_memory_service(),
    auto_create_session=True
)

@app.post("/chat")
async def chat_handler(req: ChatRequest):
    session_id = req.sessionId or "user-default-session"
    
    # Run the turn through ADK runner
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=req.message)]
    )

    reply_texts = []
    try:
        events = _runner.run_async(
            session_id=session_id,
            user_id="default-user",
            new_message=content
        )
        async for event in events:
            if hasattr(event, "content") and event.content:
                for part in event.content.parts or []:
                    if getattr(part, "text", None):
                        reply_texts.append(part.text)

        full_reply = "\n\n".join(reply_texts) if reply_texts else "(FloraGuide completed the analysis.)"
        return {"parts": [{"kind": "text", "text": full_reply}], "sessionId": session_id}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "parts": [{"kind": "text", "text": f"Error: {e}"}]})

# Serve UI static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
