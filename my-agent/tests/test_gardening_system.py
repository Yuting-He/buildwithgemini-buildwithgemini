import pytest
import uuid
from app import gardening_store as store
from app import gardening_tools as tools
from app.weather_adapter import WeatherAdapter

def test_garden_and_plant_creation():
    gid = f"g-{uuid.uuid4().hex[:6]}"
    garden = store.save_garden(gid, "Test Urban Oasis", 37.77, -122.41, "America/Los_Angeles", "San Francisco, CA")
    assert garden["name"] == "Test Urban Oasis"

    aid = f"a-{uuid.uuid4().hex[:6]}"
    area = store.save_growing_area(aid, gid, "North Balcony", "balcony", "partial shade", shelter_from_rain=True)
    assert area["shelter_from_rain"] is True

    pid = f"p-{uuid.uuid4().hex[:6]}"
    plant = store.save_plant(pid, aid, "Cherry Tomato", "Solanum lycopersicum", planting_type="container", container_size_liters=7.5)
    assert plant["name"] == "Cherry Tomato"
    assert plant["shelter_from_rain"] is True

def test_observation_overrides_watering_recommendation():
    gid = f"g_obs_{uuid.uuid4().hex[:6]}"
    aid = f"a_obs_{uuid.uuid4().hex[:6]}"
    pid = f"p_obs_{uuid.uuid4().hex[:6]}"
    jid = f"j_obs_{uuid.uuid4().hex[:6]}"

    g = store.save_garden(gid, "Obs Garden", 37.77, -122.41)
    a = store.save_growing_area(aid, gid, "Open Patio", "patio", "full sun", shelter_from_rain=False)
    p = store.save_plant(pid, aid, "Mint", planting_type="container", container_size_liters=3.0)

    # Record damp soil observation
    store.add_journal_entry(jid, pid, aid, "user_observation", "watering", "soil still feels damp at 2 inches")

    plan = tools.generate_conditional_care_plan(focus_plant_id=pid)
    tasks = plan["care_tasks"]
    assert len(tasks) > 0
    # Must hold watering and prioritize soil inspection
    water_task = next(t for t in tasks if t["plant_id"] == pid)
    assert water_task["action_type"] == "inspect_soil"
    assert "damp" in water_task["evidence_reason"].lower()

def test_sheltered_plant_rain_handling():
    gid = f"g_rain_{uuid.uuid4().hex[:6]}"
    aid_sh = f"a_sh_{uuid.uuid4().hex[:6]}"
    aid_op = f"a_op_{uuid.uuid4().hex[:6]}"
    pid_sh = f"p_sh_{uuid.uuid4().hex[:6]}"
    pid_op = f"p_op_{uuid.uuid4().hex[:6]}"

    g = store.save_garden(gid, "Rain Garden", 37.77, -122.41)
    a_sheltered = store.save_growing_area(aid_sh, gid, "Covered Porch", "porch", "partial shade", shelter_from_rain=True)
    a_open = store.save_growing_area(aid_op, gid, "Open Lawn", "garden", "full sun", shelter_from_rain=False)

    p_sh = store.save_plant(pid_sh, aid_sh, "Sheltered Fern")
    p_op = store.save_plant(pid_op, aid_op, "Lawn Hydrangea")

    plan = tools.generate_conditional_care_plan()
    tasks = plan["care_tasks"]

    sh_task = next(t for t in tasks if t["plant_id"] == pid_sh)
    assert "sheltered" in sh_task["evidence_reason"].lower() or sh_task["action_type"] == "water"

def test_travel_plan_generation():
    gid = f"g_trv_{uuid.uuid4().hex[:6]}"
    aid = f"a_trv_{uuid.uuid4().hex[:6]}"
    pid_sm = f"p_sm_{uuid.uuid4().hex[:6]}"
    pid_lg = f"p_lg_{uuid.uuid4().hex[:6]}"

    g = store.save_garden(gid, "Travel Garden", 37.77, -122.41)
    a = store.save_growing_area(aid, gid, "South Balcony", "balcony", "full sun", shelter_from_rain=True)
    p_small = store.save_plant(pid_sm, aid, "Tiny Herb", container_size_liters=1.5)
    p_large = store.save_plant(pid_lg, aid, "Olive Tree", container_size_liters=40.0)

    travel_plan = tools.plan_travel_absence(departure_date="2026-10-01", return_date="2026-10-04", available_help="Neighbor on day 2")
    assert travel_plan["status"] == "success"
    high_risks = [p["name"] for p in travel_plan["plant_risk_assessment"]["high_risk"]]
    assert "Tiny Herb" in high_risks
    assert len(travel_plan["preparation_checklist"]) > 0

from app import firestore_service

def test_firestore_plant_read_write():
    test_id = f"test-plant-{uuid.uuid4().hex[:6]}"
    saved = firestore_service.save_firestore_plant(
        plant_id=test_id,
        name="Test Lavender",
        species="Lavandula angustifolia",
        growing_area="South Balcony",
        shelter_from_rain=True,
        planting_type="container",
        container_size_liters=6.0,
        drainage_quality="excellent",
        water_needs="low"
    )
    assert saved["name"] == "Test Lavender"
    assert saved["shelter_from_rain"] is True

    fetched = firestore_service.get_firestore_plant(test_id)
    assert fetched is not None
    assert fetched["name"] == "Test Lavender"
    assert fetched["container_size_liters"] == 6.0

    obs = firestore_service.add_firestore_observation(test_id, "Fragrant blooms appearing", category="growth")
    assert obs["notes"] == "Fragrant blooms appearing"

    plants = firestore_service.list_firestore_plants()
    assert any(p["id"] == test_id for p in plants)

def test_search_gardening_knowledge_curated_and_fallback():
    # 1. Curated plant profile lookup
    basil_res = tools.search_gardening_knowledge("basil")
    assert basil_res["match_type"] == "curated_species_profile"
    assert basil_res["result"]["scientific_name"] == "Ocimum basilicum"
    assert "Tomato" in basil_res["result"]["companion_plants"][0]

    # 2. Pest & disease symptom lookup
    mildew_res = tools.search_gardening_knowledge("downy mildew")
    assert mildew_res["match_type"] == "pest_and_disease_remedy"
    assert len(mildew_res["matches"]) > 0
    assert "fuzzy spores" in mildew_res["matches"][0]["details"].lower()

    # 3. Live fallback lookup
    live_res = tools.search_gardening_knowledge("Monstera deliciosa")
    assert live_res["match_type"] in ("encyclopedia_summary", "not_found")
    if live_res["match_type"] == "encyclopedia_summary":
        assert "Monstera" in live_res["result"]["title"]

def test_daylight_and_photoperiod_api():
    # Test San Francisco coordinates
    res = tools.get_daylight_and_photoperiod(latitude=37.7749, longitude=-122.4194)
    assert res["status"] == "success"
    assert "daylight_hours" in res
    assert res["daylight_hours"] > 0
    assert "sunrise_utc" in res
    assert "sunset_utc" in res
    assert res["photoperiod_type"] in ("long_day", "short_day")

def test_agent_engine_sandbox_executor():
    from app.agent import sandbox_code_executor, SANDBOX_RESOURCE_NAME
    from google.adk.code_executors.base_code_executor import CodeExecutionInput
    assert sandbox_code_executor is not None
    assert "sandboxEnvironments" in SANDBOX_RESOURCE_NAME

    class DummySession:
        state = {}
    class DummyContext:
        session = DummySession()

    inp = CodeExecutionInput(code="water_needed_liters = 4.0 * 0.15; print(f'{water_needed_liters:.2f}')")
    res = sandbox_code_executor.execute_code(DummyContext(), inp)
    assert res.stdout.strip() == "0.60"
