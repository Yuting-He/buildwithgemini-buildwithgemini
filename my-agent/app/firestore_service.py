"""
Firestore backend service for FloraGuide.
Stores plant catalog, micro-climate profiles, and care guidelines in Cloud Firestore.
Project ID is hardcoded to prevent Agent Engine project number resolution issues.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from google.cloud import firestore

# IMPORTANT: Hardcoded project ID string as required for Agent Platform compatibility.
# Do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT because they return
# the numeric project number on Agent Engine, breaking Firestore clients.
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-04-c7b2618a365a"
PLANTS_COLLECTION = "garden_plants"

def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client bound to the hardcoded project ID."""
    return firestore.Client(project=FIRESTORE_PROJECT_ID)

def list_firestore_plants() -> List[Dict[str, Any]]:
    """Retrieves all plants from the Firestore collection."""
    db = get_firestore_client()
    docs = db.collection(PLANTS_COLLECTION).stream()
    plants = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        plants.append(data)
    return plants

def get_firestore_plant(plant_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single plant by document ID from Firestore."""
    db = get_firestore_client()
    doc = db.collection(PLANTS_COLLECTION).document(plant_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    return None

def save_firestore_plant(
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
    """Creates or updates a plant record in the Firestore collection."""
    db = get_firestore_client()
    now = datetime.now(timezone.utc).isoformat()
    plant_data = {
        "name": name,
        "species": species,
        "growing_area": growing_area,
        "shelter_from_rain": bool(shelter_from_rain),
        "planting_type": planting_type,
        "container_size_liters": container_size_liters,
        "drainage_quality": drainage_quality,
        "sun_exposure": sun_exposure,
        "water_needs": water_needs,
        "notes": notes,
        "updated_at": now
    }
    db.collection(PLANTS_COLLECTION).document(plant_id).set(plant_data, merge=True)
    plant_data["id"] = plant_id
    return plant_data

def add_firestore_observation(
    plant_id: str,
    notes: str,
    category: str = "moisture"
) -> Dict[str, Any]:
    """Appends an observation to a plant's history sub-collection in Firestore."""
    db = get_firestore_client()
    now = datetime.now(timezone.utc).isoformat()
    obs_data = {
        "timestamp": now,
        "notes": notes,
        "category": category,
        "entry_type": "user_observation"
    }
    plant_ref = db.collection(PLANTS_COLLECTION).document(plant_id)
    doc_ref = plant_ref.collection("observations").add(obs_data)
    obs_data["id"] = doc_ref[1].id
    obs_data["plant_id"] = plant_id
    return obs_data
