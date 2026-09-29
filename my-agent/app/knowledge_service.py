"""
Botanical Knowledge Service for FloraGuide.
Fetches verified plant care profiles, companion planting rules, pest/disease remedies,
and ideal environmental conditions. Uses a curated botanical database with a live
Wikipedia botanical extract fallback for arbitrary plant species.
"""

import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List

# Curated high-precision horticultural reference database
_CURATED_PLANT_DATABASE: Dict[str, Dict[str, Any]] = {
    "ocimum basilicum": {
        "common_name": "Sweet / Genovese Basil",
        "scientific_name": "Ocimum basilicum",
        "plant_family": "Lamiaceae",
        "ideal_temp_range_c": "18 - 30°C (65 - 85°F)",
        "frost_tolerance": "Extremely frost-sensitive. Leaf damage occurs at < 10°C (50°F); dies at 0°C (32°F).",
        "sun_exposure": "Full sun (6-8 hours direct sunlight daily).",
        "watering_guidelines": "Moist, well-draining soil. Highly susceptible to root rot if sitting in soggy soil. Allow top 1 inch to dry between waterings.",
        "soil_ph_preference": "6.0 - 7.5",
        "companion_plants": ["Tomato (repels thrips and hornworms)", "Peppers", "Oregano"],
        "antagonistic_plants": ["Rue", "Fennel"],
        "common_pests_and_diseases": {
            "downy mildew": "Yellow patches on top of leaves with grey-purple fuzzy spores underneath. Remedy: Ensure air circulation, avoid overhead watering, remove affected leaves immediately.",
            "aphids": "Tiny green or black sap-suckers under leaves. Remedy: Spray with diluted neem oil or insecticidal soap.",
            "root rot": "Mushy stems and dark brown roots from overwatering and poor drainage."
        },
        "care_tips": "Pinch flower buds promptly to maintain leaf vegetative growth and prevent leaves from turning bitter."
    },
    "salvia rosmarinus": {
        "common_name": "Rosemary",
        "scientific_name": "Salvia rosmarinus",
        "plant_family": "Lamiaceae",
        "ideal_temp_range_c": "12 - 28°C (55 - 82°F)",
        "frost_tolerance": "Moderately hardy (hardy down to -5°C / 23°F once established, but protect potted specimens from hard freezes).",
        "sun_exposure": "Full sun (6+ hours direct sunlight). Needs high light levels.",
        "watering_guidelines": "Drought-tolerant Mediterranean shrub. Extremely sensitive to overwatering and wet roots. Water deeply only when top 2 inches of soil are dry.",
        "soil_ph_preference": "6.0 - 7.0 (prefers gritty, rocky, or sandy well-aerated substrates).",
        "companion_plants": ["Cabbage", "Carrots", "Beans (repels cabbage moths and carrot rust flies)"],
        "antagonistic_plants": ["Basil", "Mint (competing moisture needs)"],
        "common_pests_and_diseases": {
            "powdery mildew": "White dusty powder on leaves caused by stagnant humid air. Remedy: Improve air movement and reduce watering frequency.",
            "spittlebugs": "Foamy white clusters on stems. Remedy: Hose off with a firm stream of water."
        },
        "care_tips": "Always use terracotta pots with unblocked drainage holes to allow substrate walls to breathe."
    },
    "solanum lycopersicum": {
        "common_name": "Tomato",
        "scientific_name": "Solanum lycopersicum",
        "plant_family": "Solanaceae",
        "ideal_temp_range_c": "18 - 29°C (65 - 85°F)",
        "frost_tolerance": "Zero frost tolerance. Dies at 0°C (32°F); pollen fails to set fruit above 32°C (90°F) or below 13°C (55°F).",
        "sun_exposure": "Full sun (minimum 6-8 hours direct sun daily).",
        "watering_guidelines": "Requires consistent, deep watering to prevent blossom end rot and fruit splitting. Avoid splashing foliage.",
        "soil_ph_preference": "6.2 - 6.8 (nutrient-rich, well-draining loamy soil with abundant calcium).",
        "companion_plants": ["Basil (improves flavor and repels pests)", "Marigolds (suppresses root-knot nematodes)", "Carrots", "Borage"],
        "antagonistic_plants": ["Potatoes (shared blight risk)", "Fennel", "Brassicas (cabbage/broccoli)"],
        "common_pests_and_diseases": {
            "blossom end rot": "Black sunken leather patches at bottom of fruit caused by calcium deficiency and fluctuating soil moisture.",
            "early blight": "Brown concentric rings on lower leaves. Remedy: Remove bottom 12 inches of leaves to prevent soil-splash transmission.",
            "tomato hornworm": "Large green caterpillars with white V-stripes. Remedy: Hand-pick or look for parasitic braconid wasp cocoons."
        },
        "care_tips": "Mulch the soil base heavily with straw or compost to keep moisture even and insulate root zones."
    },
    "mentha spicata": {
        "common_name": "Spearmint",
        "scientific_name": "Mentha spicata",
        "plant_family": "Lamiaceae",
        "ideal_temp_range_c": "15 - 25°C (60 - 78°F)",
        "frost_tolerance": "Very hardy. Dies back to roots during freeze and vigorously re-emerges in spring.",
        "sun_exposure": "Full sun to partial shade (tolerant of lower light than basil).",
        "watering_guidelines": "Prefers consistently moist soil. Never allow to dry out completely. Will wilt visibly when thirsty but revives quickly after watering.",
        "soil_ph_preference": "6.5 - 7.0",
        "companion_plants": ["Cabbage", "Kohlrabi", "Tomatoes (repels flea beetles and cabbage loopers)"],
        "antagonistic_plants": ["Rosemary", "Parsley", "Chamomile"],
        "common_pests_and_diseases": {
            "mint rust": "Orange/brown pustules on leaf undersides. Remedy: Cut plant back to ground level; fresh healthy foliage will regenerate.",
            "spider mites": "Tiny webbing under leaves in dry indoor air. Remedy: Increase humidity and mist leaves."
        },
        "care_tips": "Aggressive rhizomatous roots! Always grow in dedicated containers to prevent overtaking garden beds."
    },
    "lavandula angustifolia": {
        "common_name": "English Lavender",
        "scientific_name": "Lavandula angustifolia",
        "plant_family": "Lamiaceae",
        "ideal_temp_range_c": "15 - 30°C (60 - 86°F)",
        "frost_tolerance": "Hardy perennial down to -15°C (5°F) in well-drained soil.",
        "sun_exposure": "Full sun (requires 6-8+ hours of direct sun).",
        "watering_guidelines": "Drought-tolerant. Water deeply when newly planted; once established, water sparingly only during prolonged dry spells.",
        "soil_ph_preference": "6.7 - 7.3 (alkaline, lean, sandy/gravelly soil).",
        "companion_plants": ["Rosemary", "Echinacea", "Roses (repels aphids)"],
        "antagonistic_plants": ["Hostas", "Ferns (incompatible moisture needs)"],
        "common_pests_and_diseases": {
            "root rot": "The #1 killer of lavender. Caused by heavy, wet clay soil or standing water in drip trays."
        },
        "care_tips": "Prune by one-third after blooming in late summer to maintain a compact, bushy mound and prevent woody centers."
    }
}

class GardeningKnowledgeService:
    @staticmethod
    def search_knowledge(query: str) -> Dict[str, Any]:
        """
        Searches the botanical and plant disease knowledge base for the given query.
        Matches common names, scientific names, pests, and symptoms.
        Falls back to live Wikipedia botanical encyclopedia search for open queries.
        """
        q = query.strip().lower()
        words = [w for w in q.replace("?", "").replace(",", "").split() if len(w) > 2]
        
        # 1. Exact or keyword match on plant names in curated database
        for key, entry in _CURATED_PLANT_DATABASE.items():
            common = entry["common_name"].lower()
            key_words = set(key.split() + common.replace("/", " ").split())
            if q == key or q == common or q in key or q in common or key in q or any(w in key_words for w in words):
                return {
                    "source": "FloraGuide Curated Horticultural Reference",
                    "match_type": "curated_species_profile",
                    "result": entry
                }

        # 2. Check for pest/disease matches in curated database
        matching_pests = []
        for key, entry in _CURATED_PLANT_DATABASE.items():
            for pest, remedy in entry.get("common_pests_and_diseases", {}).items():
                if q in pest.lower() or pest.lower() in q or any(w in pest.lower().split() for w in words):
                    matching_pests.append({
                        "plant": entry["common_name"],
                        "issue": pest,
                        "details": remedy
                    })
        if matching_pests:
            return {
                "source": "FloraGuide Curated Horticultural Reference",
                "match_type": "pest_and_disease_remedy",
                "query": query,
                "matches": matching_pests
            }

        # 3. Live fallback: Query Wikipedia Botanical API
        # Try full query first, then individual significant nouns if full query fails
        candidates = [query] + [w for w in words if w not in ("what", "causes", "about", "care", "how", "good", "companion", "plants")]
        for cand in candidates:
            wiki_res = GardeningKnowledgeService._query_wikipedia_summary(cand)
            if wiki_res:
                return {
                    "source": "Wikipedia Botanical Encyclopedia (Live API)",
                    "match_type": "encyclopedia_summary",
                    "query": cand,
                    "result": wiki_res
                }

        return {
            "source": "FloraGuide Knowledge Service",
            "match_type": "not_found",
            "query": query,
            "message": f"No specific botanical guidelines found for '{query}'. Please verify spelling or search by botanical or common name."
        }

    @staticmethod
    def _query_wikipedia_summary(query: str) -> Optional[Dict[str, Any]]:
        """Queries the Wikipedia REST API for a concise botanical summary."""
        clean_q = urllib.parse.quote(query.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_q}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FloraGuide-GardeningAgent/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("type") in ("standard", "page") and data.get("extract"):
                return {
                    "title": data.get("title"),
                    "description": data.get("description", "Botanical subject"),
                    "summary": data.get("extract"),
                    "page_url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
                }
        except Exception:
            pass
        return None
