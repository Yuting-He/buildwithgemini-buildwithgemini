import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app import gardening_store as store
from app import gardening_tools as tools
from frontend.main import app

client = TestClient(app)

def test_garden_layout_persistence():
    gid = f"g_layout_{uuid.uuid4().hex[:6]}"
    store.save_garden(gid, "Layout Test Garden", 37.77, -122.41)

    layout_data = {
        "version": 1,
        "zoom": 1.25,
        "pan": {"x": 50, "y": -30},
        "areas": [
            {
                "id": "area-1",
                "name": "Sunny Terrace",
                "area_type": "balcony",
                "points": [{"x": 100, "y": 100}, {"x": 300, "y": 100}, {"x": 300, "y": 250}, {"x": 100, "y": 250}],
                "color": "#8d6e63",
                "texture": "balcony_wood",
                "sun_exposure": "full sun",
                "shelter_from_rain": 1
            }
        ],
        "plants": [
            {
                "id": "p-1",
                "name": "Sweet Basil",
                "x": 180,
                "y": 160,
                "area_id": "area-1",
                "scale": 1.1,
                "rotation": 0.4,
                "botanical_type": "herb"
            }
        ]
    }

    # Save layout
    saved = store.save_garden_layout(gid, layout_data)
    assert saved["garden_id"] == gid
    assert saved["layout"]["version"] == 1
    assert len(saved["layout"]["areas"]) == 1
    assert len(saved["layout"]["plants"]) == 1

    # Fetch layout
    retrieved = store.get_garden_layout(gid)
    assert retrieved is not None
    assert retrieved["areas"][0]["name"] == "Sunny Terrace"
    assert retrieved["plants"][0]["x"] == 180
    assert retrieved["plants"][0]["y"] == 160


def test_update_plant_area_and_deletion():
    gid = f"g_move_{uuid.uuid4().hex[:6]}"
    aid_1 = f"a1_{uuid.uuid4().hex[:6]}"
    aid_2 = f"a2_{uuid.uuid4().hex[:6]}"
    pid = f"p_move_{uuid.uuid4().hex[:6]}"

    store.save_garden(gid, "Move Test Garden", 37.77, -122.41)
    store.save_growing_area(aid_1, gid, "Balcony A", "balcony", "full sun", shelter_from_rain=True)
    store.save_growing_area(aid_2, gid, "Patio B", "patio", "partial shade", shelter_from_rain=False)

    p = store.save_plant(pid, aid_1, "Rosemary", planting_type="container", container_size_liters=4.0)
    assert p["area_id"] == aid_1
    assert p["shelter_from_rain"] is True

    # Reassign plant to Patio B
    updated = store.update_plant_area(pid, aid_2)
    assert updated is not None
    assert updated["area_id"] == aid_2
    assert updated["area_name"] == "Patio B"
    assert updated["shelter_from_rain"] is False

    # Delete plant
    del_plant = store.delete_plant(pid)
    assert del_plant is True

    # Confirm deletion
    deleted_p = store.get_plant(pid)
    assert deleted_p is None

    # Delete area
    del_area = store.delete_growing_area(aid_1)
    assert del_area is True
    deleted_a = store.get_growing_area(aid_1)
    assert deleted_a is None


def test_evaluate_plant_condition():
    gid = f"g_cond_{uuid.uuid4().hex[:6]}"
    aid = f"a_cond_{uuid.uuid4().hex[:6]}"
    pid = f"p_cond_{uuid.uuid4().hex[:6]}"

    store.save_garden(gid, "Health Check Garden", 37.77, -122.41)
    store.save_growing_area(aid, gid, "Sheltered Porch", "balcony", "full sun", shelter_from_rain=True)
    store.save_plant(pid, aid, "Container Mint", planting_type="container", container_size_liters=2.5)

    # Generate a care plan so there's an action for this plant
    tools.generate_conditional_care_plan(focus_plant_id=pid)

    # Evaluate condition
    cond = store.evaluate_plant_condition(pid)
    assert "status_code" in cond
    assert "color" in cond
    assert "badge_label" in cond
    assert "primary_reason" in cond
    assert "recommended_action" in cond
    assert cond["priority_rank"] in [1, 2, 3, 4]


def test_record_plant_watering():
    gid = f"g_water_{uuid.uuid4().hex[:6]}"
    aid = f"a_water_{uuid.uuid4().hex[:6]}"
    pid = f"p_water_{uuid.uuid4().hex[:6]}"

    store.save_garden(gid, "Watering Garden", 37.77, -122.41)
    store.save_growing_area(aid, gid, "Sunny Deck", "balcony", "full sun", shelter_from_rain=True)
    store.save_plant(pid, aid, "Thirsty Basil", planting_type="container", container_size_liters=3.0)

    # Generate task
    tools.generate_conditional_care_plan(focus_plant_id=pid)

    # Quick water action
    result = tools.record_plant_watering(pid, "Quick-watered 500ml from visual planner")
    assert result["status"] == "success"
    assert "condition" in result

    # Check journal has entry
    journal = store.list_journal_entries(plant_id=pid)
    assert len(journal) >= 1
    assert "Quick-watered" in journal[0]["notes"]


def test_frontend_api_endpoints():
    # 1. Save and fetch layout via API
    layout_payload = {
        "layout": {
            "version": 1,
            "areas": [{"id": "api-area-1", "name": "Rooftop Garden", "points": [{"x":0,"y":0},{"x":100,"y":0},{"x":100,"y":100},{"x":0,"y":100}]}],
            "plants": [{"id": "api-p-1", "name": "API Basil", "x": 50, "y": 50}]
        }
    }
    res_post = client.post("/api/garden/layout", json=layout_payload)
    assert res_post.status_code == 200
    assert res_post.json()["status"] == "success"

    res_get = client.get("/api/garden/layout")
    assert res_get.status_code == 200
    data = res_get.json()
    assert "layout" in data
    assert len(data["layout"]["areas"]) >= 1

    # 2. Get garden summary includes condition
    res_summary = client.get("/api/garden")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert "plants" in summary
    if len(summary["plants"]) > 0:
        first_plant = summary["plants"][0]
        assert "condition" in first_plant
        assert "color" in first_plant["condition"]

    # 3. Quick care endpoint
    if len(summary["plants"]) > 0:
        target_pid = summary["plants"][0]["id"]
        res_care = client.post(f"/api/plants/{target_pid}/quick-care", json={"action": "water", "notes": "Automated test water"})
        assert res_care.status_code == 200
        care_result = res_care.json()
        assert care_result["status"] == "success"
