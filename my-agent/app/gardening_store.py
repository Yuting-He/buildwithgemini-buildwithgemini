"""
Data persistence store for Gardens, Growing Areas, Plants, Observations, and Tasks.
Uses SQLite for robust local and container-compatible relational storage.
"""

import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

DB_PATH = os.environ.get("GARDEN_DB_PATH", os.path.join(os.path.dirname(__file__), "gardening.db"))

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Gardens table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gardens (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        timezone TEXT DEFAULT 'UTC',
        location_label TEXT,
        created_at TEXT
    )
    """)

    # Growing Areas table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS growing_areas (
        id TEXT PRIMARY KEY,
        garden_id TEXT NOT NULL,
        name TEXT NOT NULL,
        area_type TEXT NOT NULL,
        sun_exposure TEXT NOT NULL,
        shelter_from_rain INTEGER NOT NULL DEFAULT 0,
        watering_arrangements TEXT,
        notes TEXT,
        FOREIGN KEY (garden_id) REFERENCES gardens(id)
    )
    """)

    # Plants table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plants (
        id TEXT PRIMARY KEY,
        area_id TEXT NOT NULL,
        name TEXT NOT NULL,
        species TEXT,
        planting_date TEXT,
        planting_type TEXT NOT NULL DEFAULT 'container',
        container_size_liters REAL,
        substrate_type TEXT,
        drainage_quality TEXT DEFAULT 'good',
        growth_stage TEXT DEFAULT 'vegetative',
        inferred_attributes TEXT,
        created_at TEXT,
        FOREIGN KEY (area_id) REFERENCES growing_areas(id)
    )
    """)

    # Journal Entries / Observations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS journal_entries (
        id TEXT PRIMARY KEY,
        plant_id TEXT,
        area_id TEXT,
        timestamp TEXT NOT NULL,
        entry_type TEXT NOT NULL,
        category TEXT NOT NULL,
        notes TEXT NOT NULL,
        photo_url TEXT,
        metadata TEXT,
        FOREIGN KEY (plant_id) REFERENCES plants(id),
        FOREIGN KEY (area_id) REFERENCES growing_areas(id)
    )
    """)

    # Tasks / Care Plans table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        plant_id TEXT,
        area_id TEXT,
        task_date TEXT NOT NULL,
        action_type TEXT NOT NULL,
        priority TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        evidence_reason TEXT NOT NULL,
        condition_trigger TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT,
        FOREIGN KEY (plant_id) REFERENCES plants(id),
        FOREIGN KEY (area_id) REFERENCES growing_areas(id)
    )
    """)

    # Garden Layouts table for 2D/3D visual garden planner
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS garden_layouts (
        garden_id TEXT PRIMARY KEY,
        layout_json TEXT NOT NULL,
        updated_at TEXT,
        FOREIGN KEY (garden_id) REFERENCES gardens(id)
    )
    """)

    # App Settings table for preferences like active_garden_id
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

# Auto-initialize database on import
init_db()

# --- App Settings Operations ---
def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_db_connection()
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO app_settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

def get_active_garden() -> Optional[Dict[str, Any]]:
    active_id = get_setting("active_garden_id")
    if active_id:
        g = get_garden(active_id)
        if g:
            return g
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM gardens ORDER BY created_at ASC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None

def set_active_garden(garden_id: str) -> Optional[Dict[str, Any]]:
    g = get_garden(garden_id)
    if g:
        set_setting("active_garden_id", garden_id)
        return g
    return None

# --- Garden Operations ---
def save_garden(garden_id: str, name: str, latitude: float, longitude: float, timezone: str = "UTC", location_label: str = "") -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO gardens (id, name, latitude, longitude, timezone, location_label, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name=excluded.name,
        latitude=excluded.latitude,
        longitude=excluded.longitude,
        timezone=excluded.timezone,
        location_label=excluded.location_label
    """, (garden_id, name, latitude, longitude, timezone, location_label, now))
    conn.commit()
    conn.close()
    return get_garden(garden_id)

def get_garden(garden_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM gardens WHERE id = ?", (garden_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_default_garden() -> Optional[Dict[str, Any]]:
    return get_active_garden()

def list_gardens() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM gardens").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Growing Area Operations ---
def save_growing_area(area_id: str, garden_id: str, name: str, area_type: str, sun_exposure: str, shelter_from_rain: bool, watering_arrangements: str = "", notes: str = "") -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO growing_areas (id, garden_id, name, area_type, sun_exposure, shelter_from_rain, watering_arrangements, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name=excluded.name,
        area_type=excluded.area_type,
        sun_exposure=excluded.sun_exposure,
        shelter_from_rain=excluded.shelter_from_rain,
        watering_arrangements=excluded.watering_arrangements,
        notes=excluded.notes
    """, (area_id, garden_id, name, area_type, sun_exposure, 1 if shelter_from_rain else 0, watering_arrangements, notes))
    conn.commit()
    conn.close()
    return get_growing_area(area_id)

def get_growing_area(area_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM growing_areas WHERE id = ?", (area_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["shelter_from_rain"] = bool(d["shelter_from_rain"])
        return d
    return None

def list_growing_areas(garden_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if garden_id:
        rows = conn.execute("SELECT * FROM growing_areas WHERE garden_id = ?", (garden_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM growing_areas").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["shelter_from_rain"] = bool(d["shelter_from_rain"])
        result.append(d)
    return result

# --- Plant Operations ---
def save_plant(plant_id: str, area_id: str, name: str, species: Optional[str] = None, planting_date: Optional[str] = None, planting_type: str = "container", container_size_liters: Optional[float] = None, substrate_type: Optional[str] = None, drainage_quality: str = "good", growth_stage: str = "vegetative", inferred_attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    inferred_json = json.dumps(inferred_attributes or {})
    cursor.execute("""
    INSERT INTO plants (id, area_id, name, species, planting_date, planting_type, container_size_liters, substrate_type, drainage_quality, growth_stage, inferred_attributes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        area_id=excluded.area_id,
        name=excluded.name,
        species=excluded.species,
        planting_date=excluded.planting_date,
        planting_type=excluded.planting_type,
        container_size_liters=excluded.container_size_liters,
        substrate_type=excluded.substrate_type,
        drainage_quality=excluded.drainage_quality,
        growth_stage=excluded.growth_stage,
        inferred_attributes=excluded.inferred_attributes
    """, (plant_id, area_id, name, species, planting_date, planting_type, container_size_liters, substrate_type, drainage_quality, growth_stage, inferred_json, now))
    conn.commit()
    conn.close()
    return get_plant(plant_id)

def get_plant(plant_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("""
    SELECT p.*, a.name as area_name, a.shelter_from_rain, a.sun_exposure, a.garden_id
    FROM plants p
    JOIN growing_areas a ON p.area_id = a.id
    WHERE p.id = ?
    """, (plant_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["shelter_from_rain"] = bool(d["shelter_from_rain"])
        try:
            d["inferred_attributes"] = json.loads(d["inferred_attributes"] or "{}")
        except Exception:
            d["inferred_attributes"] = {}
        return d
    return None

def list_plants(area_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if area_id:
        rows = conn.execute("""
        SELECT p.*, a.name as area_name, a.shelter_from_rain, a.sun_exposure, a.garden_id
        FROM plants p
        JOIN growing_areas a ON p.area_id = a.id
        WHERE p.area_id = ?
        """, (area_id,)).fetchall()
    else:
        rows = conn.execute("""
        SELECT p.*, a.name as area_name, a.shelter_from_rain, a.sun_exposure, a.garden_id
        FROM plants p
        JOIN growing_areas a ON p.area_id = a.id
        """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["shelter_from_rain"] = bool(d["shelter_from_rain"])
        try:
            d["inferred_attributes"] = json.loads(d["inferred_attributes"] or "{}")
        except Exception:
            d["inferred_attributes"] = {}
        result.append(d)
    return result

# --- Journal & Observations ---
def add_journal_entry(entry_id: str, plant_id: Optional[str], area_id: Optional[str], entry_type: str, category: str, notes: str, photo_url: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, timestamp: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    ts = timestamp or datetime.utcnow().isoformat()
    meta_json = json.dumps(metadata or {})
    cursor.execute("""
    INSERT INTO journal_entries (id, plant_id, area_id, timestamp, entry_type, category, notes, photo_url, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (entry_id, plant_id, area_id, ts, entry_type, category, notes, photo_url, meta_json))
    conn.commit()
    conn.close()
    return get_journal_entry(entry_id)

def get_journal_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        try:
            d["metadata"] = json.loads(d["metadata"] or "{}")
        except Exception:
            d["metadata"] = {}
        return d
    return None

def list_journal_entries(plant_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if plant_id:
        rows = conn.execute("""
        SELECT j.*, p.name as plant_name
        FROM journal_entries j
        LEFT JOIN plants p ON j.plant_id = p.id
        WHERE j.plant_id = ?
        ORDER BY j.timestamp DESC
        LIMIT ?
        """, (plant_id, limit)).fetchall()
    else:
        rows = conn.execute("""
        SELECT j.*, p.name as plant_name
        FROM journal_entries j
        LEFT JOIN plants p ON j.plant_id = p.id
        ORDER BY j.timestamp DESC
        LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["metadata"] = json.loads(d["metadata"] or "{}")
        except Exception:
            d["metadata"] = {}
        result.append(d)
    return result

# --- Tasks & Plans Operations ---
def save_task(task_id: str, plant_id: Optional[str], area_id: Optional[str], task_date: str, action_type: str, priority: str, title: str, description: str, evidence_reason: str, condition_trigger: Optional[str] = None, status: str = "pending") -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO tasks (id, plant_id, area_id, task_date, action_type, priority, title, description, evidence_reason, condition_trigger, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        task_date=excluded.task_date,
        action_type=excluded.action_type,
        priority=excluded.priority,
        title=excluded.title,
        description=excluded.description,
        evidence_reason=excluded.evidence_reason,
        condition_trigger=excluded.condition_trigger,
        status=excluded.status
    """, (task_id, plant_id, area_id, task_date, action_type, priority, title, description, evidence_reason, condition_trigger, status, now))
    conn.commit()
    conn.close()
    return get_task(task_id)

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def list_tasks(status: Optional[str] = None, task_date: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    query = """
    SELECT t.*, p.name as plant_name, a.name as area_name
    FROM tasks t
    LEFT JOIN plants p ON t.plant_id = p.id
    LEFT JOIN growing_areas a ON t.area_id = a.id
    WHERE 1=1
    """
    params = []
    if status:
        query += " AND t.status = ?"
        params.append(status)
    if task_date:
        query += " AND t.task_date = ?"
        params.append(task_date)
    query += " ORDER BY CASE t.priority WHEN 'urgent' THEN 1 WHEN 'recommended' THEN 2 ELSE 3 END, t.task_date ASC"
    rows = conn.execute(query, tuple(params)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_task_status(task_id: str, status: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    conn.commit()
    conn.close()
    return get_task(task_id)

# --- Garden Layout Operations ---
def save_garden_layout(garden_id: str, layout_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    layout_str = json.dumps(layout_data)
    cursor.execute("""
    INSERT INTO garden_layouts (garden_id, layout_json, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(garden_id) DO UPDATE SET
        layout_json=excluded.layout_json,
        updated_at=excluded.updated_at
    """, (garden_id, layout_str, now))
    conn.commit()
    conn.close()
    return {"status": "success", "garden_id": garden_id, "updated_at": now, "layout": layout_data}

def get_garden_layout(garden_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM garden_layouts WHERE garden_id = ?", (garden_id,)).fetchone()
    conn.close()
    if row and row["layout_json"]:
        try:
            return json.loads(row["layout_json"])
        except Exception:
            return None
    return None

def update_plant_area(plant_id: str, area_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE plants SET area_id = ? WHERE id = ?", (area_id, plant_id))
    cursor.execute("UPDATE tasks SET area_id = ? WHERE plant_id = ?", (area_id, plant_id))
    conn.commit()
    conn.close()
    return get_plant(plant_id)

def delete_plant(plant_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE plant_id = ?", (plant_id,))
    cursor.execute("DELETE FROM journal_entries WHERE plant_id = ?", (plant_id,))
    cursor.execute("DELETE FROM plants WHERE id = ?", (plant_id,))
    conn.commit()
    conn.close()
    return True

def delete_growing_area(area_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE area_id = ?", (area_id,))
    cursor.execute("DELETE FROM journal_entries WHERE area_id = ?", (area_id,))
    cursor.execute("DELETE FROM plants WHERE area_id = ?", (area_id,))
    cursor.execute("DELETE FROM growing_areas WHERE id = ?", (area_id,))
    conn.commit()
    conn.close()
    return True

def evaluate_plant_condition(plant_id: str) -> Dict[str, Any]:
    """
    Evaluates plant condition based on pending tasks, journal observations, and environmental conditions.
    Prioritizes highest severity concern while capturing all applicable secondary concerns.
    Possible states:
    - needs_attention (urgent task or active symptom)
    - heat_concern (frost or excessive heat warning)
    - moisture_concern (excess dampness or drainage alert)
    - watering_due (watering task recommended/due)
    - observation_needed (no recent observation within 7 days)
    - doing_well (healthy, no pending issues)
    """
    plant = get_plant(plant_id)
    if not plant:
        return {
            "status_code": "unknown",
            "badge_label": "Unknown",
            "priority_rank": 99,
            "color": "#9ca3af",
            "icon": "help",
            "primary_reason": "Plant record not found",
            "secondary_concerns": [],
            "recommended_action": "Check plant registration"
        }

    # Fetch active tasks for this plant
    conn = get_db_connection()
    task_rows = conn.execute("SELECT * FROM tasks WHERE plant_id = ? AND status = 'pending'", (plant_id,)).fetchall()
    tasks = [dict(r) for r in task_rows]

    # Fetch recent observations (last 5)
    obs_rows = conn.execute("SELECT * FROM journal_entries WHERE plant_id = ? ORDER BY timestamp DESC LIMIT 5", (plant_id,)).fetchall()
    obs = [dict(r) for r in obs_rows]
    conn.close()

    concerns = []
    status_code = "doing_well"
    badge_label = "Doing well"
    priority_rank = 6
    color = "#22c55e"
    icon = "spa"
    primary_reason = "Plant is thriving with balanced moisture and light."
    recommended_action = "Continue regular monitoring and routine care."

    # Analyze tasks & observations
    urgent_task = next((t for t in tasks if t.get("priority") == "urgent"), None)
    frost_heat_task = next((t for t in tasks if "frost" in (t.get("title", "") + t.get("evidence_reason", "")).lower() or "heat" in (t.get("title", "") + t.get("evidence_reason", "")).lower() or t.get("action_type") == "shelter_protection"), None)
    moisture_task = next((t for t in tasks if t.get("action_type") == "inspect_soil" or "damp" in t.get("evidence_reason", "").lower() or "overwater" in t.get("evidence_reason", "").lower()), None)
    water_task = next((t for t in tasks if t.get("action_type") == "water" or "water" in t.get("title", "").lower()), None)
    symptom_obs = next((o for o in obs if o.get("category") == "symptom" or "wilt" in o.get("notes", "").lower() or "droop" in o.get("notes", "").lower() or "pest" in o.get("notes", "").lower() or "yellow" in o.get("notes", "").lower()), None)

    # Check date of latest observation
    latest_obs = obs[0] if obs else None
    has_recent_obs = False
    if latest_obs and latest_obs.get("timestamp"):
        try:
            obs_dt = datetime.fromisoformat(latest_obs["timestamp"].replace("Z", "+00:00"))
            if obs_dt.tzinfo is None:
                obs_dt = obs_dt.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - obs_dt).days < 7:
                has_recent_obs = True
        except Exception:
            has_recent_obs = True

    # Identify potential concerns
    if frost_heat_task:
        concerns.append({
            "code": "heat_concern",
            "label": "Heat or dryness concern" if "heat" in (frost_heat_task.get("title", "") + frost_heat_task.get("evidence_reason", "")).lower() else "Frost / Temperature concern",
            "rank": 1,
            "color": "#f59e0b",
            "icon": "thermostat",
            "reason": frost_heat_task["evidence_reason"],
            "action": frost_heat_task["description"]
        })

    if moisture_task:
        concerns.append({
            "code": "moisture_concern",
            "label": "Excess moisture concern",
            "rank": 2,
            "color": "#06b6d4",
            "icon": "water_damage",
            "reason": moisture_task["evidence_reason"],
            "action": moisture_task["description"]
        })

    if water_task:
        concerns.append({
            "code": "watering_due",
            "label": "Watering check due",
            "rank": 3,
            "color": "#0288d1",
            "icon": "water_drop",
            "reason": water_task["evidence_reason"],
            "action": water_task["description"]
        })

    # Only add generic needs_attention if there is an unhandled urgent task or disease/pest symptom
    other_urgent = urgent_task if (urgent_task and urgent_task["id"] not in [t["id"] for t in [frost_heat_task, moisture_task, water_task] if t]) else None
    other_symptom = symptom_obs if (symptom_obs and not (frost_heat_task or moisture_task)) else None
    if other_urgent or other_symptom:
        reason = other_urgent["evidence_reason"] if other_urgent else f"Reported issue: {symptom_obs['notes']}"
        action = other_urgent["description"] if other_urgent else "Inspect plant foliage and root zone immediately."
        concerns.append({
            "code": "needs_attention",
            "label": "Needs attention",
            "rank": 0,
            "color": "#ef4444",
            "icon": "error",
            "reason": reason,
            "action": action
        })

    if not has_recent_obs:
        concerns.append({
            "code": "observation_needed",
            "label": "Observation needed",
            "rank": 5,
            "color": "#8b5cf6",
            "icon": "visibility",
            "reason": "No journal observation recorded in the past 7 days.",
            "action": "Check soil moisture, leaf growth, and general vitality."
        })

    # Pick highest priority concern
    if concerns:
        concerns.sort(key=lambda c: c["rank"])
        highest = concerns[0]
        status_code = highest["code"]
        badge_label = highest["label"]
        priority_rank = highest["rank"]
        color = highest["color"]
        icon = highest["icon"]
        primary_reason = highest["reason"]
        recommended_action = highest["action"]
        secondary_concerns = [f"{c['label']}: {c['reason']}" for c in concerns[1:]]
    else:
        secondary_concerns = []

    return {
        "status_code": status_code,
        "badge_label": badge_label,
        "priority_rank": priority_rank,
        "color": color,
        "icon": icon,
        "primary_reason": primary_reason,
        "secondary_concerns": secondary_concerns,
        "recommended_action": recommended_action,
        "pending_tasks_count": len(tasks),
        "latest_observation": latest_obs
    }


# --- Fully Populated Example Garden Seeder ---
def create_or_reset_example_garden(garden_id: str = "example-garden", switch_to: bool = True) -> Dict[str, Any]:
    """
    Creates or resets the populated FloraGuide Demonstration Garden.
    Features distinct zones:
    1. Sunny Patio: Potted olive tree, rosemary, lavender (containers)
    2. Vegetable Beds: Two raised beds with tomatoes, lettuce, and carrots
    3. Herb Corner: Basil, mint, and parsley in individual containers under pergola
    4. Shaded Flower Bed: Hydrangea and ferns in an organic in-ground bed
    5. Garden Path: Connecting stepping-stone walkway tying the garden together

    Includes full profiles, realistic journal observations, and active tasks demonstrating
    all 4 key plant conditions: Healthy, Watering Check Due, Heat Concern, and Excess Moisture Concern.
    """
    save_garden(
        garden_id=garden_id,
        name="FloraGuide Demonstration Garden",
        latitude=37.7749,
        longitude=-122.4194,
        timezone="America/Los_Angeles",
        location_label="Demonstration Garden (San Francisco)"
    )

    conn = get_db_connection()
    cursor = conn.cursor()
    # Clean up previous entities for this garden to avoid stale duplicate entries
    demo_plant_ids = [
        "p-olive", "p-rosemary", "p-lavender", "p-tomato", "p-lettuce",
        "p-carrot", "p-basil", "p-mint", "p-parsley", "p-hydrangea", "p-ferns"
    ]
    placeholders = ','.join('?' for _ in demo_plant_ids)
    cursor.execute(f"DELETE FROM tasks WHERE plant_id IN ({placeholders}) OR area_id IN (SELECT id FROM growing_areas WHERE garden_id = ?)", (*demo_plant_ids, garden_id))
    cursor.execute(f"DELETE FROM journal_entries WHERE plant_id IN ({placeholders}) OR area_id IN (SELECT id FROM growing_areas WHERE garden_id = ?)", (*demo_plant_ids, garden_id))
    cursor.execute(f"DELETE FROM plants WHERE id IN ({placeholders}) OR area_id IN (SELECT id FROM growing_areas WHERE garden_id = ?)", (*demo_plant_ids, garden_id))
    cursor.execute("DELETE FROM growing_areas WHERE garden_id = ?", (garden_id,))
    conn.commit()
    conn.close()

    # --- 1. Growing Areas ---
    save_growing_area(
        area_id="area-sunny-patio",
        garden_id=garden_id,
        name="Sunny Patio",
        area_type="patio",
        sun_exposure="full sun",
        shelter_from_rain=False,
        watering_arrangements="Drip line & manual watering can",
        notes="Warm south-facing stone terrace with terracotta pots."
    )

    save_growing_area(
        area_id="area-veg-bed-1",
        garden_id=garden_id,
        name="Vegetable Bed 1",
        area_type="raised bed",
        sun_exposure="full sun",
        shelter_from_rain=False,
        watering_arrangements="Soaker hose",
        notes="Cedar raised bed, 12 inches deep with nutrient-rich compost."
    )

    save_growing_area(
        area_id="area-veg-bed-2",
        garden_id=garden_id,
        name="Vegetable Bed 2",
        area_type="raised bed",
        sun_exposure="full sun",
        shelter_from_rain=False,
        watering_arrangements="Soaker hose",
        notes="Cedar raised bed for leafy greens and root crops."
    )

    save_growing_area(
        area_id="area-herb-corner",
        garden_id=garden_id,
        name="Herb Corner",
        area_type="patio",
        sun_exposure="partial sun",
        shelter_from_rain=True,
        watering_arrangements="Hand watered daily",
        notes="Sheltered culinary herb nook under porch pergola eaves."
    )

    save_growing_area(
        area_id="area-shaded-bed",
        garden_id=garden_id,
        name="Shaded Flower Bed",
        area_type="ground",
        sun_exposure="deep shade",
        shelter_from_rain=False,
        watering_arrangements="Ambient rainfall with supplementary hose",
        notes="Dappled light under mature canopy with rich organic mulch."
    )

    save_growing_area(
        area_id="area-garden-path",
        garden_id=garden_id,
        name="Garden Path",
        area_type="path",
        sun_exposure="partial sun",
        shelter_from_rain=False,
        watering_arrangements="None (gravel walkway)",
        notes="Connecting walkway making layout feel like a real garden."
    )

    now_utc = datetime.now(timezone.utc)

    # --- 2. Plants ---
    # Sunny Patio
    save_plant(
        plant_id="p-olive",
        area_id="area-sunny-patio",
        name="Dwarf Olive Tree",
        species='Olea europaea "Arbequina"',
        planting_date=(now_utc - timedelta(days=180)).strftime("%Y-%m-%d"),
        planting_type="container",
        container_size_liters=45.0,
        substrate_type="mediterranean gravel blend",
        drainage_quality="excellent",
        growth_stage="mature"
    )
    save_plant(
        plant_id="p-rosemary",
        area_id="area-sunny-patio",
        name="Tuscan Rosemary",
        species="Salvia rosmarinus",
        planting_date=(now_utc - timedelta(days=90)).strftime("%Y-%m-%d"),
        planting_type="container",
        container_size_liters=8.0,
        substrate_type="sandy loam mix",
        drainage_quality="excellent",
        growth_stage="vegetative"
    )
    save_plant(
        plant_id="p-lavender",
        area_id="area-sunny-patio",
        name="English Lavender",
        species='Lavandula angustifolia "Munstead"',
        planting_date=(now_utc - timedelta(days=120)).strftime("%Y-%m-%d"),
        planting_type="container",
        container_size_liters=6.0,
        substrate_type="well-draining rocky mix",
        drainage_quality="excellent",
        growth_stage="flowering"
    )

    # Vegetable Beds
    save_plant(
        plant_id="p-tomato",
        area_id="area-veg-bed-1",
        name="San Marzano Tomatoes",
        species="Solanum lycopersicum",
        planting_date=(now_utc - timedelta(days=55)).strftime("%Y-%m-%d"),
        planting_type="raised bed",
        container_size_liters=0.0,
        substrate_type="organic compost & garden loam",
        drainage_quality="good",
        growth_stage="fruiting"
    )
    save_plant(
        plant_id="p-lettuce",
        area_id="area-veg-bed-2",
        name="Butterhead Lettuce",
        species="Lactuca sativa",
        planting_date=(now_utc - timedelta(days=30)).strftime("%Y-%m-%d"),
        planting_type="raised bed",
        container_size_liters=0.0,
        substrate_type="rich garden loam",
        drainage_quality="moderate",
        growth_stage="vegetative"
    )
    save_plant(
        plant_id="p-carrot",
        area_id="area-veg-bed-2",
        name="Nantes Carrots",
        species="Daucus carota sativus",
        planting_date=(now_utc - timedelta(days=40)).strftime("%Y-%m-%d"),
        planting_type="raised bed",
        container_size_liters=0.0,
        substrate_type="loose sandy loam",
        drainage_quality="good",
        growth_stage="vegetative"
    )

    # Herb Corner
    save_plant(
        plant_id="p-basil",
        area_id="area-herb-corner",
        name="Sweet Genovese Basil",
        species="Ocimum basilicum",
        planting_date=(now_utc - timedelta(days=25)).strftime("%Y-%m-%d"),
        planting_type="container",
        container_size_liters=4.0,
        substrate_type="moist potting soil",
        drainage_quality="good",
        growth_stage="vegetative"
    )
    save_plant(
        plant_id="p-mint",
        area_id="area-herb-corner",
        name="Spearmint",
        species="Mentha spicata",
        planting_date=(now_utc - timedelta(days=60)).strftime("%Y-%m-%d"),
        planting_type="container",
        container_size_liters=5.0,
        substrate_type="organic potting mix",
        drainage_quality="good",
        growth_stage="vegetative"
    )
    save_plant(
        plant_id="p-parsley",
        area_id="area-herb-corner",
        name="Flat-Leaf Italian Parsley",
        species="Petroselinum crispum",
        planting_date=(now_utc - timedelta(days=45)).strftime("%Y-%m-%d"),
        planting_type="container",
        container_size_liters=3.5,
        substrate_type="rich potting compost",
        drainage_quality="good",
        growth_stage="vegetative"
    )

    # Shaded Flower Bed
    save_plant(
        plant_id="p-hydrangea",
        area_id="area-shaded-bed",
        name="French Hydrangea",
        species="Hydrangea macrophylla",
        planting_date=(now_utc - timedelta(days=150)).strftime("%Y-%m-%d"),
        planting_type="in-ground",
        container_size_liters=0.0,
        substrate_type="acidic moist garden loam",
        drainage_quality="moderate",
        growth_stage="flowering"
    )
    save_plant(
        plant_id="p-ferns",
        area_id="area-shaded-bed",
        name="Ostrich Ferns",
        species="Matteuccia struthiopteris",
        planting_date=(now_utc - timedelta(days=200)).strftime("%Y-%m-%d"),
        planting_type="in-ground",
        container_size_liters=0.0,
        substrate_type="humus-rich woodland soil",
        drainage_quality="good",
        growth_stage="vegetative"
    )

    # --- 3. Sample Observations / Journal Entries ---
    entries = [
        ("obs-olive-1", "p-olive", "area-sunny-patio", "observation", "general", "Flourishing canopy with healthy silvery foliage. Excellent soil drainage in terra-cotta planter.", now_utc - timedelta(days=1)),
        ("obs-rosemary-1", "p-rosemary", "area-sunny-patio", "observation", "general", "Upper 2 inches of gritty container mix feel dry. Growth is compact and aromatic.", now_utc - timedelta(days=1)),
        ("obs-lavender-1", "p-lavender", "area-sunny-patio", "observation", "flowering", "Fragrant purple flower spikes blooming vigorously; pollinator bees actively visiting.", now_utc - timedelta(days=2)),
        ("obs-tomato-1", "p-tomato", "area-veg-bed-1", "observation", "fruiting", "Heavy green fruit clusters swelling quickly; staked and tied main vine securely.", now_utc - timedelta(days=1)),
        ("obs-lettuce-1", "p-lettuce", "area-veg-bed-2", "observation", "observation", "Dense crisp heads forming. Soil heavily saturated from recent watering; lower leaves resting on damp compost.", now_utc - timedelta(days=1)),
        ("obs-carrot-1", "p-carrot", "area-veg-bed-2", "observation", "growth", "Feathery green foliage growing uniformly. Thinned seedlings to 2-inch spacing.", now_utc - timedelta(days=3)),
        ("obs-basil-1", "p-basil", "area-herb-corner", "observation", "symptom", "Noted afternoon leaf drooping and slight leaf-tip curling during intense 32°C heatwave.", now_utc - timedelta(days=1)),
        ("obs-mint-1", "p-mint", "area-herb-corner", "observation", "harvest", "Vigorous aromatic growth contained in planter; pinched shoots for culinary tea.", now_utc - timedelta(days=2)),
        ("obs-parsley-1", "p-parsley", "area-herb-corner", "observation", "harvest", "Healthy new growth emerging from crown; outer stems harvested for kitchen prep.", now_utc - timedelta(days=2)),
        ("obs-hydrangea-1", "p-hydrangea", "area-shaded-bed", "observation", "flowering", "Lush violet-blue bloom globes in peak flower. Low bed depression holding excess runoff.", now_utc - timedelta(days=1)),
        ("obs-ferns-1", "p-ferns", "area-shaded-bed", "observation", "growth", "Lush arching fronds unfurling in cool dappled shade under organic mulch layer.", now_utc - timedelta(days=2))
    ]

    for eid, pid, aid, etype, cat, note, ts in entries:
        add_journal_entry(
            entry_id=eid,
            plant_id=pid,
            area_id=aid,
            entry_type=etype,
            category=cat,
            notes=note,
            timestamp=ts.isoformat()
        )

    # --- 4. Sample Tasks (Driving Clearly Labeled Conditions) ---
    today_str = now_utc.strftime("%Y-%m-%d")

    # Watering check due: Tomatoes & Rosemary
    save_task(
        task_id="task-water-tomato",
        plant_id="p-tomato",
        area_id="area-veg-bed-1",
        task_date=today_str,
        action_type="water",
        priority="recommended",
        title="Watering check: Deep root hydration",
        description="Water deeply at base using soaker line until 6-inch soil depth is moist.",
        evidence_reason="Active fruit swelling stage; soil moisture sensor reads low in root zone."
    )
    save_task(
        task_id="task-water-rosemary",
        plant_id="p-rosemary",
        area_id="area-sunny-patio",
        task_date=today_str,
        action_type="water",
        priority="recommended",
        title="Watering check: Container soil check",
        description="Water moderately until slight drainage occurs from container base.",
        evidence_reason="Upper 2 inches of gritty container mix are dry to the touch."
    )

    # Heat concern: Sweet Genovese Basil
    save_task(
        task_id="task-heat-basil",
        plant_id="p-basil",
        area_id="area-herb-corner",
        task_date=today_str,
        action_type="shelter_protection",
        priority="urgent",
        title="Heat concern: Afternoon sun stress",
        description="Shift container 2 feet into pergola shade and mist surrounding stones.",
        evidence_reason="Intense afternoon heatwave (32°C / 90°F) causing temporary leaf curl and transpiration stress."
    )

    # Excess-moisture concern: French Hydrangea & Butterhead Lettuce
    save_task(
        task_id="task-moisture-hydrangea",
        plant_id="p-hydrangea",
        area_id="area-shaded-bed",
        task_date=today_str,
        action_type="inspect_soil",
        priority="urgent",
        title="Excess-moisture concern: Shaded soil saturation",
        description="Gently aerate mulch around root flare and ensure runoff drainage channel is clear.",
        evidence_reason="Excess moisture alert: drainage depression retaining rainwater runoff in shaded bed."
    )
    save_task(
        task_id="task-moisture-lettuce",
        plant_id="p-lettuce",
        area_id="area-veg-bed-2",
        task_date=today_str,
        action_type="inspect_soil",
        priority="recommended",
        title="Excess-moisture concern: Damp bottom foliage",
        description="Allow top 1 inch of raised bed soil to dry before next watering.",
        evidence_reason="Persistent surface dampness on dense compost mulch; risk of lower leaf rot."
    )

    # --- 5. Persisted 2D/3D Geometry Layout ---
    layout_data = {
        "areas": [
            {
                "id": "area-sunny-patio",
                "name": "Sunny Patio",
                "area_type": "patio",
                "shape_type": "polygon",
                "points": [
                    {"x": 100, "y": 120},
                    {"x": 340, "y": 120},
                    {"x": 370, "y": 220},
                    {"x": 350, "y": 340},
                    {"x": 230, "y": 370},
                    {"x": 100, "y": 350}
                ],
                "rotation": 0
            },
            {
                "id": "area-veg-bed-1",
                "name": "Vegetable Bed 1",
                "area_type": "raised bed",
                "shape_type": "rect",
                "points": [
                    {"x": 520, "y": 120},
                    {"x": 740, "y": 120},
                    {"x": 740, "y": 230},
                    {"x": 520, "y": 230}
                ],
                "rotation": 0
            },
            {
                "id": "area-veg-bed-2",
                "name": "Vegetable Bed 2",
                "area_type": "raised bed",
                "shape_type": "rect",
                "points": [
                    {"x": 520, "y": 270},
                    {"x": 740, "y": 270},
                    {"x": 740, "y": 380},
                    {"x": 520, "y": 380}
                ],
                "rotation": 0
            },
            {
                "id": "area-herb-corner",
                "name": "Herb Corner",
                "area_type": "patio",
                "shape_type": "polygon",
                "points": [
                    {"x": 100, "y": 410},
                    {"x": 300, "y": 410},
                    {"x": 320, "y": 530},
                    {"x": 240, "y": 600},
                    {"x": 100, "y": 600}
                ],
                "rotation": 0
            },
            {
                "id": "area-shaded-bed",
                "name": "Shaded Flower Bed",
                "area_type": "ground",
                "shape_type": "freehand",
                "points": [
                    {"x": 480, "y": 460},
                    {"x": 650, "y": 430},
                    {"x": 790, "y": 480},
                    {"x": 820, "y": 580},
                    {"x": 720, "y": 640},
                    {"x": 530, "y": 630},
                    {"x": 460, "y": 540}
                ],
                "rotation": 0
            },
            {
                "id": "area-garden-path",
                "name": "Garden Path",
                "area_type": "path",
                "shape_type": "polygon",
                "points": [
                    {"x": 340, "y": 220},
                    {"x": 480, "y": 240},
                    {"x": 520, "y": 380},
                    {"x": 490, "y": 440},
                    {"x": 350, "y": 440},
                    {"x": 330, "y": 390},
                    {"x": 430, "y": 390},
                    {"x": 430, "y": 290},
                    {"x": 340, "y": 270}
                ],
                "rotation": 0
            }
        ],
        "plants": [
            {"id": "p-olive", "x": 170, "y": 200, "scale": 1.4},
            {"id": "p-rosemary", "x": 270, "y": 180, "scale": 1.1},
            {"id": "p-lavender", "x": 290, "y": 270, "scale": 1.0},
            {"id": "p-tomato", "x": 630, "y": 175, "scale": 1.3},
            {"id": "p-lettuce", "x": 580, "y": 325, "scale": 0.95},
            {"id": "p-carrot", "x": 680, "y": 325, "scale": 0.85},
            {"id": "p-basil", "x": 160, "y": 480, "scale": 1.0},
            {"id": "p-mint", "x": 230, "y": 470, "scale": 1.0},
            {"id": "p-parsley", "x": 190, "y": 540, "scale": 0.95},
            {"id": "p-hydrangea", "x": 590, "y": 530, "scale": 1.35},
            {"id": "p-ferns", "x": 710, "y": 550, "scale": 1.15}
        ]
    }
    save_garden_layout(garden_id, layout_data)

    if switch_to:
        set_active_garden(garden_id)

    return {
        "status": "success",
        "garden_id": garden_id,
        "growing_areas_count": 6,
        "plants_count": 11,
        "layout": layout_data
    }

