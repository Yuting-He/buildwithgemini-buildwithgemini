# My agent: FloraGuide (Personal Gardening Assistant)
One-liner: A context-aware gardening assistant that understands your growing areas and micro-environments, monitors real environmental conditions, maintains plant histories and observation journals, and delivers conditional care and travel plans.

Tool coverage:
- Memory: Remembers garden constraints (water access, inability to move heavy pots, physical access), user preferences, and historical plant care patterns.
- Tools: Look up real weather (Open-Meteo), solar daylight & photoperiod (Sunrise-Sunset API), manage growing areas and plants, log timestamped journal observations, generate conditional care plans, plan travel absences, botanical knowledge search, and read/write Cloud Firestore (`garden_plants`).
- Catalog/UI: Growing areas (balcony/patio/greenhouse/ground), plant profiles (persisted in Cloud Firestore `garden_plants`), daily task checklists, and travel readiness plans rendered as structured A2UI cards and multi-view web interface.
- Storage: Cloud Firestore collection `garden_plants` on project `qwiklabs-gcp-04-c7b2618a365a`.
- Image gen: Visual plant identification guidance or garden visual mockups (optional).
- Sandbox: Remote Agent Engine Sandbox (`AgentEngineSandboxCodeExecutor`) for safe cloud execution of Python computations (evapotranspiration, water deficit, frost/heat rules).

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Deterministic weather adapter with ET0 calculation, solar photoperiod tracking (Sunrise-Sunset API), Agent Engine Python Sandbox, sheltered vs open rain exposure rules, observation-driven overrides, Cloud Firestore backend, multi-view responsive UI (Today, My Garden, Journal, Plans, Assistant).
