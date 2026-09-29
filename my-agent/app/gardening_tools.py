"""
Agent Function Tools for FloraGuide.
Bridges SQLite storage, the weather adapter, deterministic rules, and the LLM.
"""

import uuid
import re
import base64
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

from . import gardening_store as store
from .weather_adapter import WeatherAdapter

# Hardcoded constants for Cloud Storage & Vertex AI
GCS_BUCKET_NAME = "bwg3-qwiklabs-gcp-04-c7b2618a365a"
GCP_PROJECT_ID = "qwiklabs-gcp-04-c7b2618a365a"

def get_garden_summary(garden_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves the complete profile of the garden, all growing areas, and all plants.
    Also returns recent journal observations and pending tasks.
    """
    garden = store.get_garden(garden_id) if garden_id else store.get_default_garden()
    if not garden:
        # Provide default garden if none created yet
        garden = store.save_garden(
            garden_id="default-garden",
            name="My Home Garden",
            latitude=37.7749,
            longitude=-122.4194,
            timezone="America/Los_Angeles",
            location_label="San Francisco, CA"
        )
        # Create a sample sheltered area
        store.save_growing_area(
            area_id="balcony-1",
            garden_id=garden["id"],
            name="Covered Balcony",
            area_type="balcony",
            sun_exposure="partial sun",
            shelter_from_rain=True,
            watering_arrangements="Manual watering can",
            notes="Sheltered from direct rainfall by upper balcony overhang."
        )

    areas = store.list_growing_areas(garden["id"])
    area_ids = {a["id"] for a in areas}
    all_plants = store.list_plants()
    plants = [p for p in all_plants if p.get("area_id") in area_ids]
    for p in plants:
        p["condition"] = store.evaluate_plant_condition(p["id"])
    plant_ids = {p["id"] for p in plants}
    all_journal = store.list_journal_entries(limit=50)
    recent_journal = [j for j in all_journal if j.get("plant_id") in plant_ids or j.get("area_id") in area_ids][:10]
    all_tasks = store.list_tasks(status="pending")
    pending_tasks = [t for t in all_tasks if t.get("plant_id") in plant_ids or t.get("area_id") in area_ids]

    return {
        "garden": garden,
        "growing_areas": areas,
        "plants": plants,
        "recent_observations": recent_journal,
        "pending_tasks": pending_tasks
    }

def check_local_weather(garden_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches real-time environmental data and 7-day forecast for the garden's location.
    Explicitly discloses data freshness/staleness and highlights environmental risks (frost, heatwave, rain).
    """
    garden = store.get_garden(garden_id) if garden_id else store.get_default_garden()
    lat = garden["latitude"] if garden and garden.get("latitude") else 37.7749
    lon = garden["longitude"] if garden and garden.get("longitude") else -122.4194
    tz = garden["timezone"] if garden and garden.get("timezone") else "UTC"

    weather = WeatherAdapter.fetch_weather(lat, lon, tz)
    return weather

def add_or_update_growing_area(
    name: str,
    area_type: str,
    sun_exposure: str,
    shelter_from_rain: bool,
    watering_arrangements: str = "",
    area_id: Optional[str] = None,
    notes: str = ""
) -> Dict[str, Any]:
    """
    Adds a new growing area or updates an existing one (e.g., balcony, patio, greenhouse, raised bed, open garden).
    Note: shelter_from_rain is critical because sheltered plants receive zero direct rainfall.
    """
    garden = store.get_default_garden()
    if not garden:
        garden = store.save_garden("default-garden", "My Home Garden", 37.7749, -122.4194)

    target_id = area_id or f"area-{uuid.uuid4().hex[:6]}"
    area = store.save_growing_area(
        area_id=target_id,
        garden_id=garden["id"],
        name=name,
        area_type=area_type,
        sun_exposure=sun_exposure,
        shelter_from_rain=shelter_from_rain,
        watering_arrangements=watering_arrangements,
        notes=notes
    )
    return {"status": "success", "growing_area": area}

def add_or_update_plant(
    area_id: str,
    name: str,
    species: Optional[str] = None,
    planting_date: Optional[str] = None,
    planting_type: str = "container",
    container_size_liters: Optional[float] = None,
    substrate_type: Optional[str] = None,
    drainage_quality: str = "good",
    growth_stage: str = "vegetative",
    plant_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Registers a new plant or updates an existing plant profile in a specified growing area.
    """
    target_id = plant_id or f"plant-{uuid.uuid4().hex[:6]}"
    plant = store.save_plant(
        plant_id=target_id,
        area_id=area_id,
        name=name,
        species=species,
        planting_date=planting_date,
        planting_type=planting_type,
        container_size_liters=container_size_liters,
        substrate_type=substrate_type,
        drainage_quality=drainage_quality,
        growth_stage=growth_stage
    )
    return {"status": "success", "plant": plant}

def record_plant_observation(
    notes: str,
    plant_id: Optional[str] = None,
    area_id: Optional[str] = None,
    entry_type: str = "user_observation",
    category: str = "general",
    photo_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Logs an observation, action taken, or symptom into the plant journal.
    Examples of notes: 'soil still feels damp at 2 inches', 'watered 500ml', 'leaves drooped this afternoon'.
    """
    entry_id = f"obs-{uuid.uuid4().hex[:6]}"
    entry = store.add_journal_entry(
        entry_id=entry_id,
        plant_id=plant_id,
        area_id=area_id,
        entry_type=entry_type,
        category=category,
        notes=notes,
        photo_url=photo_url
    )
    return {"status": "success", "journal_entry": entry}

def record_plant_watering(plant_id: str, notes: str = "Watered thoroughly until slight drainage") -> Dict[str, Any]:
    """
    Records a watering care action for a plant, marks any pending watering tasks as completed,
    and returns the updated plant condition.
    """
    plant = store.get_plant(plant_id)
    if not plant:
        return {"status": "error", "message": f"Plant {plant_id} not found"}

    entry = record_plant_observation(
        notes=notes,
        plant_id=plant_id,
        area_id=plant.get("area_id"),
        entry_type="care_action",
        category="watering"
    )

    # Mark pending watering tasks for this plant as completed
    tasks = store.list_tasks(status="pending")
    for t in tasks:
        if t.get("plant_id") == plant_id and (t.get("action_type") == "water" or "water" in t.get("title", "").lower()):
            store.update_task_status(t["id"], "completed")

    condition = store.evaluate_plant_condition(plant_id)
    return {
        "status": "success",
        "journal_entry": entry.get("journal_entry"),
        "condition": condition
    }

def generate_conditional_care_plan(focus_plant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyzes current plant records, micro-climates (sheltered vs open), latest user observations
    (e.g., damp soil), and real local weather forecast to create a practical, conditional care plan.
    """
    plants = [store.get_plant(focus_plant_id)] if focus_plant_id else store.list_plants()
    plants = [p for p in plants if p]
    if not plants:
        return {"status": "error", "message": "No plants registered yet. Please add a plant first."}

    garden = store.get_default_garden()
    lat = garden["latitude"] if garden and garden.get("latitude") else 37.7749
    lon = garden["longitude"] if garden and garden.get("longitude") else -122.4194
    tz = garden["timezone"] if garden and garden.get("timezone") else "UTC"

    weather = WeatherAdapter.fetch_weather(lat, lon, tz)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch recent observations (last 48 hours)
    recent_obs = store.list_journal_entries(limit=20)
    obs_by_plant: Dict[str, List[Dict[str, Any]]] = {}
    for o in recent_obs:
        if o.get("plant_id"):
            obs_by_plant.setdefault(o["plant_id"], []).append(o)

    generated_tasks = []

    for p in plants:
        p_id = p["id"]
        p_name = p["name"]
        is_sheltered = p.get("shelter_from_rain", False)
        plant_obs = obs_by_plant.get(p_id, [])

        # Check for recent moisture observation
        recent_damp_soil = any("damp" in o["notes"].lower() or "moist" in o["notes"].lower() for o in plant_obs)
        recent_dry_soil = any("dry" in o["notes"].lower() for o in plant_obs)

        # Weather conditions
        rain_sum_3d = sum(d.get("precipitation_sum_mm", 0) for d in weather.get("forecast_days", [])[:3])
        temp_max_3d = max((d.get("temp_max_c", 20) for d in weather.get("forecast_days", [])[:3]), default=20)
        frost_risk = weather.get("risks", {}).get("frost_risk_next_72h", False)

        # --- Rule 1: Frost Risk ---
        if frost_risk and p.get("planting_type") == "container":
            t = store.save_task(
                task_id=f"task-frost-{p_id}-{today_str}",
                plant_id=p_id,
                area_id=p.get("area_id"),
                task_date=today_str,
                action_type="shelter_protection",
                priority="urgent",
                title=f"Protect {p_name} from impending frost",
                description=f"Move container against a south-facing wall or bring indoors overnight.",
                evidence_reason=f"Forecast indicates minimum temperatures <= 2°C in the next 72 hours.",
                condition_trigger="If nighttime temp is forecast to fall below 3°C."
            )
            generated_tasks.append(t)

        # --- Rule 2: Watering with Shelter & Observation Awareness ---
        if recent_damp_soil:
            t = store.save_task(
                task_id=f"task-water-{p_id}-{today_str}",
                plant_id=p_id,
                area_id=p.get("area_id"),
                task_date=today_str,
                action_type="inspect_soil",
                priority="recommended",
                title=f"Check soil moisture for {p_name} (hold watering)",
                description=f"Do not water today. Inspect top 2 inches of soil; only water if dry below the surface.",
                evidence_reason=f"Recent journal observation noted soil is still damp. Overwatering poses root rot risk.",
                condition_trigger="Soil must feel dry to the first knuckle before applying water."
            )
            generated_tasks.append(t)
        elif is_sheltered:
            reason = f"Plant is in a sheltered area ({p.get('area_name', 'sheltered')}) and receives zero ambient rainfall."
            if rain_sum_3d > 10.0:
                reason += f" Outdoor rainfall of {rain_sum_3d:.1f}mm will NOT reach this pot."
            
            t = store.save_task(
                task_id=f"task-water-{p_id}-{today_str}",
                plant_id=p_id,
                area_id=p.get("area_id"),
                task_date=today_str,
                action_type="water",
                priority="recommended",
                title=f"Manual watering check for {p_name}",
                description=f"Check moisture and water thoroughly until slight drainage occurs.",
                evidence_reason=reason,
                condition_trigger="Water if top layer is dry; ensure saucer does not hold standing water."
            )
            generated_tasks.append(t)
        else: # Uncovered / Open ground
            if rain_sum_3d >= 15.0:
                t = store.save_task(
                    task_id=f"task-water-{p_id}-{today_str}",
                    plant_id=p_id,
                    area_id=p.get("area_id"),
                    task_date=today_str,
                    action_type="hold_watering",
                    priority="optional",
                    title=f"Skip watering for {p_name} (rain incoming)",
                    description=f"Sufficient ambient rainfall ({rain_sum_3d:.1f}mm) expected across the next 3 days.",
                    evidence_reason=f"Unsheltered plant will receive natural precipitation.",
                    condition_trigger="Check drainage to ensure bed/pot does not become waterlogged."
                )
                generated_tasks.append(t)
            else:
                t = store.save_task(
                    task_id=f"task-water-{p_id}-{today_str}",
                    plant_id=p_id,
                    area_id=p.get("area_id"),
                    task_date=today_str,
                    action_type="water",
                    priority="recommended",
                    title=f"Water {p_name}",
                    description=f"Water soil evenly in early morning.",
                    evidence_reason=f"Low forecast rainfall ({rain_sum_3d:.1f}mm) and high temperatures ({temp_max_3d}°C).",
                    condition_trigger="Verify soil is not waterlogged before watering."
                )
                generated_tasks.append(t)

    return {
        "status": "success",
        "weather_summary": {
            "current_temp_f": weather["current"]["temperature_f"],
            "rain_forecast_3d_mm": round(sum(d.get("precipitation_sum_mm", 0) for d in weather.get("forecast_days", [])[:3]), 1),
            "is_stale": weather.get("is_stale", False)
        },
        "care_tasks": generated_tasks
    }

def plan_travel_absence(
    departure_date: str,
    return_date: str,
    available_help: str = "none",
    existing_watering_arrangements: str = "manual"
) -> Dict[str, Any]:
    """
    Creates a customized absence plan for departure and return periods.
    Groups plants by risk (small containers vs established ground beds), checks weather forecasts,
    and outlines pre-trip prep, absence arrangements, and return inspections.
    """
    plants = store.list_plants()
    garden = store.get_default_garden()
    lat = garden["latitude"] if garden and garden.get("latitude") else 37.7749
    lon = garden["longitude"] if garden and garden.get("longitude") else -122.4194
    tz = garden["timezone"] if garden and garden.get("timezone") else "UTC"

    weather = WeatherAdapter.fetch_weather(lat, lon, tz)

    high_risk_plants = []
    moderate_risk_plants = []
    low_risk_plants = []

    for p in plants:
        ptype = p.get("planting_type", "container")
        size = p.get("container_size_liters") or 5.0
        sheltered = p.get("shelter_from_rain", False)

        if ptype == "container" and size <= 5.0:
            high_risk_plants.append({
                "name": p["name"],
                "reason": f"Small container ({size}L) dries out quickly; requires wick, reservoir, or shade."
            })
        elif ptype == "container" and sheltered:
            moderate_risk_plants.append({
                "name": p["name"],
                "reason": f"Sheltered pot will receive no rain even during storms."
            })
        else:
            low_risk_plants.append({
                "name": p["name"],
                "reason": "Established ground planting or large pot with moisture buffer."
            })

    # Prepare prep tasks
    prep_actions = [
        "Do NOT blindly overwater all plants before leaving (prevents root rot).",
        "Move sensitive small containers out of harsh midday sun into dappled shade.",
        "Prune dead foliage and harvest ripe produce to reduce water transpiration.",
        "Top-dress pots with a 1-inch layer of organic mulch or compost to retain moisture."
    ]

    absence_care = []
    if available_help.lower() != "none":
        absence_care.append(f"Brief helper: Only water high-risk plants ({', '.join([p['name'] for p in high_risk_plants]) or 'none'}) halfway through absence.")
    else:
        absence_care.append("Set up self-watering wicks (cotton rope in water bottle) or inverted glass bulb for small pots.")

    return_checks = [
        "Inspect each pot for moisture depth before applying any water.",
        "Check for signs of pest flare-ups or fungal issues under high humidity.",
        "Gradually re-introduce shaded containers back into full sun over 2 days."
    ]

    return {
        "status": "success",
        "trip_dates": {"departure": departure_date, "return": return_date},
        "plant_risk_assessment": {
            "high_risk": high_risk_plants,
            "moderate_risk": moderate_risk_plants,
            "low_risk": low_risk_plants
        },
        "preparation_checklist": prep_actions,
        "absence_mitigation": absence_care,
        "return_inspection": return_checks
    }

# --- Cloud Firestore Integration Tools ---
from . import firestore_service

def list_garden_plants_firestore() -> Dict[str, Any]:
    """
    Retrieves all cataloged garden plants directly from Cloud Firestore.
    Returns plant details including micro-climate, container sizing, shelter status, and water needs.
    """
    plants = firestore_service.list_firestore_plants()
    return {
        "status": "success",
        "source": "Cloud Firestore (collection: garden_plants)",
        "plant_count": len(plants),
        "plants": plants
    }

def get_garden_plant_firestore(plant_id: str) -> Dict[str, Any]:
    """
    Fetches a specific plant by its Firestore document ID (e.g. 'plant-basil-01').
    """
    plant = firestore_service.get_firestore_plant(plant_id)
    if not plant:
        return {"status": "error", "message": f"Plant with ID '{plant_id}' not found in Firestore."}
    return {"status": "success", "plant": plant}

def add_or_update_firestore_plant(
    plant_id: str,
    name: str,
    species: str,
    growing_area: str,
    shelter_from_rain: bool,
    planting_type: str = "container",
    container_size_liters: Optional[float] = None,
    drainage_quality: str = "good",
    sun_exposure: str = "full sun",
    water_needs: str = "moderate",
    notes: str = ""
) -> Dict[str, Any]:
    """
    Creates or updates a plant record in the Cloud Firestore collection.
    Use this to persist new plants across sessions in the cloud database.
    """
    saved = firestore_service.save_firestore_plant(
        plant_id=plant_id,
        name=name,
        species=species,
        growing_area=growing_area,
        shelter_from_rain=shelter_from_rain,
        planting_type=planting_type,
        container_size_liters=container_size_liters,
        drainage_quality=drainage_quality,
        sun_exposure=sun_exposure,
        water_needs=water_needs,
        notes=notes
    )
    return {"status": "success", "saved_plant": saved}

def log_firestore_plant_observation(
    plant_id: str,
    notes: str,
    category: str = "moisture"
) -> Dict[str, Any]:
    """
    Records an observation (e.g., 'soil damp', 'foliage yellowing') into the plant's history sub-collection in Firestore.
    """
    obs = firestore_service.add_firestore_observation(plant_id=plant_id, notes=notes, category=category)
    return {"status": "success", "recorded_observation": obs}

# --- Botanical Knowledge Base Tool ---
from .knowledge_service import GardeningKnowledgeService

def search_gardening_knowledge(query: str) -> Dict[str, Any]:
    """
    Searches botanical reference data, pest remedies, and companion planting guides.
    Useful for looking up ideal temperatures, sunlight requirements, watering baselines,
    companion/antagonistic plants, and treatment for plant diseases like mildew, blight, or pests.
    Falls back to live botanical encyclopedia data for plants not in the curated catalog.
    
    Args:
        query: Botanical name, common plant name, or pest/symptom term (e.g. 'Ocimum basilicum', 'Rosemary', 'downy mildew', 'blossom end rot').
    """
    return GardeningKnowledgeService.search_knowledge(query)

# --- Solar Photoperiod & Sunlight Tool (Sunrise-Sunset API) ---
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone

def get_daylight_and_photoperiod(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches real solar photoperiod, daylight length, sunrise, sunset, and solar noon times
    from the free public Sunrise-Sunset API (https://sunrise-sunset.org/api).
    Essential for determining vegetative photoperiod, fruiting triggers (short-day vs long-day plants),
    and available direct sunlight hours for balconies and outdoor growing areas.

    Args:
        latitude: Latitude coordinate (defaults to current garden latitude if omitted).
        longitude: Longitude coordinate (defaults to current garden longitude if omitted).
        date: Target date in 'YYYY-MM-DD' format (or 'today' by default).
    """
    gardens = store.list_gardens(); g = gardens[0] if gardens else None
    lat = latitude if latitude is not None else (g["latitude"] if g else 37.7749)
    lng = longitude if longitude is not None else (g["longitude"] if g else -122.4194)
    target_date = date or "today"

    url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&date={urllib.parse.quote(target_date)}&formatted=0"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FloraGuide-GardeningAgent/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        if data.get("status") == "OK" and "results" in data:
            res = data["results"]
            day_length_sec = res.get("day_length", 0)
            hours = round(day_length_sec / 3600.0, 2)
            
            # Horticultural classification based on photoperiod
            photoperiod_type = "long_day" if hours >= 12.0 else "short_day"
            
            return {
                "status": "success",
                "source": "Sunrise-Sunset Free Public API (sunrise-sunset.org)",
                "location": {"latitude": lat, "longitude": lng},
                "date": target_date,
                "daylight_hours": hours,
                "photoperiod_type": photoperiod_type,
                "sunrise_utc": res.get("sunrise"),
                "sunset_utc": res.get("sunset"),
                "solar_noon_utc": res.get("solar_noon"),
                "civil_twilight_begin_utc": res.get("civil_twilight_begin"),
                "civil_twilight_end_utc": res.get("civil_twilight_end"),
                "horticultural_context": (
                    f"With {hours} hours of daylight, plants experience a {photoperiod_type.replace('_', '-')} photoperiod. "
                    "Full-sun fruiting crops (tomatoes, peppers) require at least 6-8 hours of direct exposure within this daylight window."
                )
            }
        else:
            return {"status": "error", "message": f"API returned non-OK status: {data.get('status')}"}
    except Exception as exc:
        return {"status": "error", "message": f"Failed to fetch daylight photoperiod: {exc}"}

# --- Google Maps Platform Tools (Geocoding & Places API New) ---
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def _get_google_maps_auth():
    """
    Retrieves the Google Maps API key from GOOGLE_MAPS_API_KEY (or GOOGLE_API_KEY).
    Also retrieves project ID and OAuth token from default Google credentials as a resilient fallback.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")
    token = None
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-c7b2618a365a")
    try:
        import google.auth
        import google.auth.transport.requests
        creds, proj = google.auth.default()
        if proj:
            project_id = proj
        if creds:
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            token = creds.token
    except Exception:
        pass
    return api_key, token, project_id


def geocode_address(address: str) -> Dict[str, Any]:
    """
    Geocodes an address or location description into geographical coordinates (latitude and longitude)
    using the Google Maps Geocoding API REST endpoint directly.

    Args:
        address: Street address, landmark, city, or postal code (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dict with status, name, address, and location (latitude, longitude).
    """
    if not address or not address.strip():
        return {"status": "error", "message": "Address parameter cannot be empty."}

    api_key, token, project_id = _get_google_maps_auth()
    encoded_addr = urllib.parse.quote(address.strip())

    # Strategy 1: Call Google Cloud Geocoding REST endpoint (v4)
    v4_url = f"https://geocode.googleapis.com/v4/geocode/address?addressQuery={encoded_addr}"
    headers = {}
    if api_key:
        headers["X-Goog-Api-Key"] = api_key
    if project_id:
        headers["X-Goog-User-Project"] = project_id

    try:
        resp = requests.get(v4_url, headers=headers, timeout=10)
        # If API key has service restriction or 403, retry with OAuth bearer token
        if resp.status_code == 403 and token:
            oauth_headers = {
                "Authorization": f"Bearer {token}",
                "X-Goog-User-Project": project_id
            }
            resp = requests.get(v4_url, headers=oauth_headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                r0 = results[0]
                loc = r0.get("location", {})
                lat = loc.get("latitude")
                lng = loc.get("longitude")
                fmt_addr = r0.get("formattedAddress", address)
                return {
                    "status": "success",
                    "name": fmt_addr,
                    "address": fmt_addr,
                    "location": {"latitude": lat, "longitude": lng},
                    "results": [
                        {
                            "name": r.get("formattedAddress", address),
                            "address": r.get("formattedAddress", address),
                            "location": r.get("location", {})
                        }
                        for r in results
                    ]
                }
    except Exception:
        pass

    # Strategy 2: Call Maps Geocoding JSON REST endpoint
    maps_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}"
    if api_key:
        maps_url += f"&key={api_key}"
    try:
        resp = requests.get(maps_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK" and data.get("results"):
                r0 = data["results"][0]
                geometry_loc = r0.get("geometry", {}).get("location", {})
                lat = geometry_loc.get("lat")
                lng = geometry_loc.get("lng")
                fmt_addr = r0.get("formatted_address", address)
                return {
                    "status": "success",
                    "name": fmt_addr,
                    "address": fmt_addr,
                    "location": {"latitude": lat, "longitude": lng},
                    "results": [
                        {
                            "name": r.get("formatted_address", address),
                            "address": r.get("formatted_address", address),
                            "location": {
                                "latitude": r.get("geometry", {}).get("location", {}).get("lat"),
                                "longitude": r.get("geometry", {}).get("location", {}).get("lng")
                            }
                        }
                        for r in data["results"]
                    ]
                }
    except Exception as exc:
        return {"status": "error", "message": f"Geocoding request failed: {exc}"}

    return {"status": "error", "message": f"Could not geocode address: {address}"}


def find_nearby_places(
    place_type: str = "garden_center",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    address: Optional[str] = None,
    radius_meters: float = 5000.0
) -> Dict[str, Any]:
    """
    Finds nearby places of a given type (e.g. 'garden_center', 'florist', 'park', 'hardware_store')
    using the Places API (New) searchNearby REST endpoint directly.

    Args:
        place_type: Type of place to search for (e.g. 'garden_center', 'nursery', 'park', 'hardware_store', 'store').
        latitude: Latitude of search center (defaults to garden location if omitted).
        longitude: Longitude of search center (defaults to garden location if omitted).
        address: Optional address to center the search around if latitude/longitude are omitted.
        radius_meters: Search radius around the center point in meters (default 5000.0, up to 50000.0).

    Returns:
        Dict with status and list of places containing key fields: name, address, and location.
    """
    # If coordinates are missing, resolve from address or garden profile
    if latitude is None or longitude is None:
        if address:
            geo_res = geocode_address(address)
            if geo_res.get("status") == "success" and "location" in geo_res:
                latitude = geo_res["location"].get("latitude")
                longitude = geo_res["location"].get("longitude")

    if latitude is None or longitude is None:
        gardens = store.list_gardens()
        g = gardens[0] if gardens else None
        latitude = g["latitude"] if g else 37.7749
        longitude = g["longitude"] if g else -122.4194

    api_key, token, project_id = _get_google_maps_auth()
    url = "https://places.googleapis.com/v1/places:searchNearby"

    # Confirmed headers from Developer Knowledge MCP
    headers = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }
    if api_key:
        headers["X-Goog-Api-Key"] = api_key
    if project_id:
        headers["X-Goog-User-Project"] = project_id

    body = {
        "includedTypes": [place_type],
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude)
                },
                "radius": float(radius_meters)
            }
        }
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=12)

        # Resilient fallback: if API key is blocked or has service restrictions, use OAuth Bearer token
        if resp.status_code == 403 and token:
            oauth_headers = {
                "Content-Type": "application/json",
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
                "Authorization": f"Bearer {token}",
                "X-Goog-User-Project": project_id
            }
            resp = requests.post(url, json=body, headers=oauth_headers, timeout=12)

        if resp.status_code == 200:
            data = resp.json()
            raw_places = data.get("places", [])
            places_list = []
            for p in raw_places:
                name = p.get("displayName", {}).get("text", "")
                addr = p.get("formattedAddress", "")
                loc = p.get("location", {})
                places_list.append({
                    "name": name,
                    "address": addr,
                    "location": {
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude")
                    }
                })
            return {
                "status": "success",
                "place_type": place_type,
                "center": {"latitude": latitude, "longitude": longitude},
                "radius_meters": radius_meters,
                "places": places_list
            }
        else:
            return {
                "status": "error",
                "status_code": resp.status_code,
                "message": f"Places API returned error: {resp.text}"
            }
    except Exception as exc:
        return {"status": "error", "message": f"Places API request failed: {exc}"}


async def generate_plant_video(
    plant_name: str,
    topic: Optional[str] = "growth time-lapse",
    aspect_ratio: Optional[str] = "16:9",
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    Generates a short botanical, time-lapse, or plant care video for an item in the garden
    using Google's Omni model (gemini-omni-flash-preview) in the global region.

    The video bytes are handled completely in-memory:
    1. Saved to the session artifacts panel using tool_context.save_artifact.
    2. Uploaded to the public Cloud Storage bucket (bwg3-qwiklabs-gcp-04-c7b2618a365a)
       and the public https URL is returned.
    Does NOT write the video to local disk or return a local file path.

    Args:
        plant_name: Name or species of the plant or garden item (e.g., 'Tomato', 'Basil', 'Lavender', 'Hydrangea').
        topic: Specific scene or theme to visualize (e.g. 'growth time-lapse', 'pruning technique demo', 'botanical watering and morning dew', 'sunlight and blooming flowers').
        aspect_ratio: Video aspect ratio ('16:9' or '9:16'). Defaults to '16:9'.
        tool_context: Injected ADK ToolContext used to save the video artifact into the active session.

    Returns:
        Dict containing status, plant_name, topic, artifact_filename, artifact_saved, and public_url.
    """
    clean_name = plant_name.strip() if plant_name else "Garden Plant"
    clean_topic = (topic or "growth time-lapse").strip()
    valid_aspect_ratio = aspect_ratio if aspect_ratio in ("16:9", "9:16") else "16:9"

    # Descriptive, vivid botanical video generation prompt
    prompt = (
        f"A cinematic, high-definition botanical video of {clean_name}: {clean_topic}. "
        f"Natural garden sunlight, healthy foliage, vivid colors, smooth motion, high detail."
    )

    try:
        # 1. Generate video using Gemini Omni model on global Vertex AI endpoint
        client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT_ID,
            location="global"
        )

        interaction = await asyncio.to_thread(
            client.interactions.create,
            model="gemini-omni-flash-preview",
            input=prompt,
            response_format={
                "type": "video",
                "aspect_ratio": valid_aspect_ratio
            }
        )

        # 2. Extract in-memory video bytes from model response
        video_bytes = None
        if hasattr(interaction, "output_video") and interaction.output_video:
            if getattr(interaction.output_video, "data", None):
                video_bytes = base64.b64decode(interaction.output_video.data)

        if not video_bytes and hasattr(interaction, "steps"):
            for step in getattr(interaction, "steps", []):
                for content in getattr(step, "content", []):
                    if getattr(content, "type", None) == "video" and getattr(content, "data", None):
                        video_bytes = base64.b64decode(content.data)
                        break

        if not video_bytes:
            return {
                "status": "error",
                "message": "The Omni model completed the interaction, but no video bytes were returned."
            }

        # 3. Create unique artifact and object names
        safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_name.lower()) or "plant_item"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        artifact_filename = f"{safe_slug}_{timestamp}.mp4"
        gcs_object_name = f"videos/{safe_slug}_{timestamp}.mp4"

        # 4. Upload in-memory video bytes to public Cloud Storage bucket
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(gcs_object_name)
        blob.upload_from_string(video_bytes, content_type="video/mp4")
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{gcs_object_name}"

        # 5. Save video artifact via tool_context into session
        artifact_saved = False
        if tool_context is not None:
            try:
                artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
                await tool_context.save_artifact(
                    filename=artifact_filename,
                    artifact=artifact_part,
                    custom_metadata={
                        "model": "gemini-omni-flash-preview",
                        "region": "global",
                        "plant_name": clean_name,
                        "topic": clean_topic,
                        "public_url": public_url,
                        "aspect_ratio": valid_aspect_ratio
                    }
                )
                artifact_saved = True
            except Exception as art_err:
                logging.getLogger(__name__).warning("Failed to save artifact to tool_context: %s", art_err)

        return {
            "status": "success",
            "plant_name": clean_name,
            "topic": clean_topic,
            "artifact_filename": artifact_filename,
            "artifact_saved": artifact_saved,
            "public_url": public_url,
            "duration": "5s",
            "aspect_ratio": valid_aspect_ratio,
            "message": (
                f"Generated short botanical video for '{clean_name}' ({clean_topic}) using gemini-omni-flash-preview. "
                f"Saved to session artifacts as '{artifact_filename}' and uploaded to public Cloud Storage: {public_url}"
            )
        }

    except Exception as exc:
        logging.getLogger(__name__).error("Video generation failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate video using gemini-omni-flash-preview: {exc}"
        }


# Expose alias for flexible agent discovery
generate_gardening_video = generate_plant_video

