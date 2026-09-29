import os
import pytest
from dotenv import load_dotenv
from app import gardening_tools as tools
from app.agent import root_agent

load_dotenv()

def test_api_key_env_and_not_hardcoded():
    # 1. API key must be saved in .env as GOOGLE_MAPS_API_KEY or GOOGLE_API_KEY
    api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_API_KEY")
    assert api_key is not None, "GOOGLE_MAPS_API_KEY (or GOOGLE_API_KEY) should be set in .env"
    assert len(api_key) > 20, "API key should be a valid API key string"

    # 2. Key must not be hardcoded in app source files
    app_dir = os.path.join(os.path.dirname(__file__), "..", "app")
    for root, _, files in os.walk(app_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as py_file:
                    content = py_file.read()
                    assert api_key not in content, f"Hardcoded API key found in {f}!"


def test_geocode_address_tool():
    # Test geocoding a known address
    address = "1600 Amphitheatre Pkwy, Mountain View, CA"
    result = tools.geocode_address(address)

    assert result["status"] == "success"
    # Must return key fields: name, address, location
    assert "name" in result
    assert "address" in result
    assert "location" in result

    loc = result["location"]
    assert "latitude" in loc
    assert "longitude" in loc
    assert abs(loc["latitude"] - 37.422) < 0.05
    assert abs(loc["longitude"] - (-122.084)) < 0.05


def test_find_nearby_places_tool():
    # Test finding nearby parks or places around San Francisco Civic Center
    result = tools.find_nearby_places(
        place_type="park",
        latitude=37.7749,
        longitude=-122.4194,
        radius_meters=2000.0
    )

    assert result["status"] == "success"
    assert "places" in result
    assert len(result["places"]) > 0

    first_place = result["places"][0]
    # Must return key fields: name, address, location
    assert "name" in first_place
    assert "address" in first_place
    assert "location" in first_place
    assert "latitude" in first_place["location"]
    assert "longitude" in first_place["location"]


def test_tools_registered_in_agent():
    # Check that root_agent has geocode_address and find_nearby_places in its tool list
    tool_names = [getattr(t, "__name__", getattr(t, "name", str(t))) for t in root_agent.tools]
    assert "geocode_address" in tool_names
    assert "find_nearby_places" in tool_names
