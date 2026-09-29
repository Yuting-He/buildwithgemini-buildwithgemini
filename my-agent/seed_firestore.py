"""
Seed script to populate Cloud Firestore with initial FloraGuide garden plants.
Uses the hardcoded GCP project ID: qwiklabs-gcp-04-c7b2618a365a.
"""

from app.firestore_service import save_firestore_plant, add_firestore_observation, list_firestore_plants

def seed_plants():
    print("Seeding initial plants into Cloud Firestore...")

    # Plant 1: Genovese Basil on sheltered balcony
    save_firestore_plant(
        plant_id="plant-basil-01",
        name="Genovese Basil",
        species="Ocimum basilicum",
        growing_area="South-Facing Balcony",
        shelter_from_rain=True,
        planting_type="container",
        container_size_liters=4.0,
        drainage_quality="good",
        sun_exposure="full sun",
        water_needs="moderate to high",
        notes="Under roof overhang. Sheltered from ambient rain, requires manual watering."
    )
    add_firestore_observation("plant-basil-01", "Soil still feels damp 2 inches below surface", category="moisture")

    # Plant 2: Tuscan Rosemary on sheltered balcony
    save_firestore_plant(
        plant_id="plant-rosemary-01",
        name="Tuscan Rosemary",
        species="Salvia rosmarinus",
        growing_area="South-Facing Balcony",
        shelter_from_rain=True,
        planting_type="container",
        container_size_liters=12.0,
        drainage_quality="excellent",
        sun_exposure="full sun",
        water_needs="low",
        notes="Drought-tolerant, terracotta pot under overhang. Sensitive to overwatering."
    )

    # Plant 3: Early Girl Tomato in open outdoor raised bed
    save_firestore_plant(
        plant_id="plant-tomato-01",
        name="Early Girl Tomato",
        species="Solanum lycopersicum",
        growing_area="Open Raised Bed",
        shelter_from_rain=False,
        planting_type="ground",
        container_size_liters=None,
        drainage_quality="good",
        sun_exposure="full sun",
        water_needs="high",
        notes="Directly exposed to weather and natural rainfall. Supported by tomato cage."
    )
    add_firestore_observation("plant-tomato-01", "Flower clusters forming; foliage healthy and green", category="growth")

    # Plant 4: Mint in small container on patio
    save_firestore_plant(
        plant_id="plant-mint-01",
        name="Spearmint",
        species="Mentha spicata",
        growing_area="Open Patio",
        shelter_from_rain=False,
        planting_type="container",
        container_size_liters=2.5,
        drainage_quality="moderate",
        sun_exposure="partial shade",
        water_needs="high",
        notes="Small pot dries out rapidly during warm afternoons; keep confined to pot to avoid spreading."
    )

    seeded = list_firestore_plants()
    print(f"Successfully seeded {len(seeded)} plants into Firestore collection 'garden_plants':")
    for p in seeded:
        print(f"  - [{p['id']}] {p['name']} ({p['species']}) in {p['growing_area']} (Sheltered: {p['shelter_from_rain']})")

if __name__ == "__main__":
    seed_plants()
