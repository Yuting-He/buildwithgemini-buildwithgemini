"""
Weather Adapter integrating Open-Meteo with caching, staleness disclosure,
historical vs forecast separation, and deterministic environmental risk analysis.
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# In-memory cache for weather data
_WEATHER_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_MINUTES = 60
STALE_THRESHOLD_HOURS = 6

class WeatherAdapter:
    @staticmethod
    def fetch_weather(lat: float, lon: float, tz_str: str = "auto") -> Dict[str, Any]:
        """
        Fetch real forecast and recent conditions from Open-Meteo.
        Includes temperature, precipitation, humidity, wind, and reference evapotranspiration (ET0).
        """
        cache_key = f"{round(lat, 2)},{round(lon, 2)}"
        now = datetime.now(timezone.utc)

        # Check cache
        if cache_key in _WEATHER_CACHE:
            cached = _WEATHER_CACHE[cache_key]
            fetch_time = datetime.fromisoformat(cached["fetched_at"])
            age_hours = (now - fetch_time).total_seconds() / 3600.0
            if age_hours < (CACHE_TTL_MINUTES / 60.0):
                cached_data = dict(cached["data"])
                cached_data["is_stale"] = age_hours >= STALE_THRESHOLD_HOURS
                cached_data["data_age_hours"] = round(age_hours, 1)
                return cached_data

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,evapotranspiration",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,et0_fao_evapotranspiration,wind_speed_10m_max",
            "timezone": tz_str if tz_str != "UTC" else "auto"
        }
        url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FloraGuide-GardenAgent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            parsed = WeatherAdapter._parse_open_meteo(data, lat, lon)
            _WEATHER_CACHE[cache_key] = {
                "fetched_at": now.isoformat(),
                "data": parsed
            }
            parsed["is_stale"] = False
            parsed["data_age_hours"] = 0.0
            return parsed

        except Exception as e:
            # Fallback if cached data exists (even if stale)
            if cache_key in _WEATHER_CACHE:
                cached = _WEATHER_CACHE[cache_key]
                fetch_time = datetime.fromisoformat(cached["fetched_at"])
                age_hours = (now - fetch_time).total_seconds() / 3600.0
                fallback_data = dict(cached["data"])
                fallback_data["is_stale"] = True
                fallback_data["data_age_hours"] = round(age_hours, 1)
                fallback_data["fetch_error"] = str(e)
                return fallback_data
            
            # Synthetic safe default if completely unreachable
            return WeatherAdapter._fallback_weather_data(lat, lon, str(e))

    @staticmethod
    def _parse_open_meteo(raw: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
        current = raw.get("current", {})
        daily = raw.get("daily", {})
        daily_time = daily.get("time", [])

        forecast_days = []
        for i in range(min(7, len(daily_time))):
            forecast_days.append({
                "date": daily_time[i],
                "temp_max_c": daily.get("temperature_2m_max", [0])[i],
                "temp_min_c": daily.get("temperature_2m_min", [0])[i],
                "precipitation_sum_mm": daily.get("precipitation_sum", [0])[i],
                "precip_probability_max": daily.get("precipitation_probability_max", [0])[i],
                "et0_mm": daily.get("et0_fao_evapotranspiration", [0])[i] if daily.get("et0_fao_evapotranspiration") else None,
                "wind_speed_max_kmh": daily.get("wind_speed_10m_max", [0])[i]
            })

        temp_c = current.get("temperature_2m", 20.0)
        temp_f = round(temp_c * 9/5 + 32, 1)

        # Environmental risk flags
        frost_risk = False
        heatwave_risk = False
        heavy_rain_risk = False
        high_evaporation = False

        for day in forecast_days[:3]:
            if day["temp_min_c"] <= 2.0:
                frost_risk = True
            if day["temp_max_c"] >= 32.0:
                heatwave_risk = True
            if day["precipitation_sum_mm"] >= 20.0:
                heavy_rain_risk = True
            if day.get("et0_mm") and day["et0_mm"] >= 5.0:
                high_evaporation = True

        return {
            "source": "Open-Meteo API (ECMWF/GFS/DWD models)",
            "latitude": lat,
            "longitude": lon,
            "timezone": raw.get("timezone", "UTC"),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "current": {
                "temperature_c": temp_c,
                "temperature_f": temp_f,
                "relative_humidity_percent": current.get("relative_humidity_2m", 50),
                "apparent_temperature_c": current.get("apparent_temperature", temp_c),
                "precipitation_mm": current.get("precipitation", 0.0),
                "wind_speed_kmh": current.get("wind_speed_10m", 0.0)
            },
            "forecast_days": forecast_days,
            "risks": {
                "frost_risk_next_72h": frost_risk,
                "heatwave_risk_next_72h": heatwave_risk,
                "heavy_rain_risk_next_72h": heavy_rain_risk,
                "high_evaporation_rate": high_evaporation
            }
        }

    @staticmethod
    def _fallback_weather_data(lat: float, lon: float, error_msg: str) -> Dict[str, Any]:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {
            "source": "Offline Fallback (Live API unavailable)",
            "latitude": lat,
            "longitude": lon,
            "timezone": "UTC",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "is_stale": True,
            "data_age_hours": 999.0,
            "fetch_error": error_msg,
            "current": {
                "temperature_c": 18.0,
                "temperature_f": 64.4,
                "relative_humidity_percent": 60,
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 10.0
            },
            "forecast_days": [
                {
                    "date": today_str,
                    "temp_max_c": 21.0,
                    "temp_min_c": 12.0,
                    "precipitation_sum_mm": 0.0,
                    "precip_probability_max": 10,
                    "et0_mm": 3.0,
                    "wind_speed_max_kmh": 12.0
                }
            ],
            "risks": {
                "frost_risk_next_72h": False,
                "heatwave_risk_next_72h": False,
                "heavy_rain_risk_next_72h": False,
                "high_evaporation_rate": False
            }
        }
