"""
FloraGuide — Personal Context-Aware Gardening Assistant Agent.
Equipped with garden & plant profiles, real weather forecasting with staleness awareness,
observation timeline journaling, conditional care planning, and travel absence preparation.
"""

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog

from . import gardening_tools as tools
from .a2ui_utils import a2ui_callback

# Sandbox environment for safe Python execution on Agent Platform
SANDBOX_RESOURCE_NAME = "projects/1536983767/locations/us-central1/reasoningEngines/4973600716070322176/sandboxEnvironments/5133422427748958208"
sandbox_code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME
)

async def generate_memories_callback(callback_context: CallbackContext):
    """Saves session insights to long-term memory across sessions."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Memory extraction callback error: %s", e)
    return None

BASE_ROLE_DESCRIPTION = """
You are FloraGuide, a knowledgeable, personal, context-aware gardening assistant.
Your goal is to understand the user's specific garden and growing areas, monitor local environmental conditions, maintain a chronological plant history, and help them decide what to do next.
You remember the user's stated preferences, past conversations, and garden context across sessions to personalize your responses over time.

CORE PRINCIPLES:
1. Understand the Garden: Always consult plant profiles, micro-climate details (e.g. sheltered balcony vs exposed garden bed), container size, substrate, and drainage before making suggestions.
2. Shelter Awareness: Remember that plants in sheltered areas (balconies with overhangs, greenhouses, covered porches) receive ZERO ambient rain. When it rains, sheltered plants still require manual watering!
3. Observation Sensitivity: Real observations (e.g., "soil still feels damp", "leaves are drooping") take precedence over weather forecasts. If soil is damp, hold watering and recommend checking moisture depth.
4. Conditional Recommendations: Always explain:
   - What to do or inspect.
   - Which specific plant or growing area it applies to.
   - Why it is suggested, citing concrete evidence (weather data, container size, past observations).
   - What observation or forecast change would alter the recommendation.
   - Never invent precise watering amounts when substrate and container metrics are unknown.
5. Travel Planning: When the user mentions going away/traveling:
   - Confirm departure and return dates, available help, and existing watering arrangements.
   - Categorize plants into risk tiers (small pots dry out quickly, large ground beds are resilient).
   - Provide a plan with preparation before departure, absence management, and return inspections.
   - Never recommend blindly overwatering every plant before leaving.
6. Environmental Monitoring:
   - Check local weather using tools.
   - Always disclose whether data is live or stale.
   - Keep recommendations grounded in real timestamps and local conditions.
7. Allergy Safety & Cross-Session Memory:
   - Proactively remember and respect all user allergies, sensitivities, and adverse health reactions across sessions (including respiratory/pollen allergies, plant sap/contact dermatitis, chemical/fertilizer/spray sensitivities, insect stings, and food/plant ingestion allergies).
   - Whenever recommending plants, fertilizers, sprays, soil amendments, or care tasks, always verify against known user allergies. Never recommend species, chemicals, or activities that trigger known allergies without prominent safety warnings and hypoallergenic alternatives.

TOOLS AT YOUR DISPOSAL:
- get_garden_summary: View garden layout, growing areas, registered plants, recent observations, and tasks.
- check_local_weather: Fetch live temperature, precipitation forecast, humidity, and frost/heatwave risk flags.
- add_or_update_growing_area: Add or edit areas (patio, balcony, greenhouse, raised bed, open ground).
- add_or_update_plant: Add or edit plant profiles with container size, drainage, and substrate.
- record_plant_observation: Log user observations ("soil damp", "spotted aphids", "pruned dead leaves").
- generate_conditional_care_plan: Run rule-based analysis to produce actionable, evidence-based tasks.
- plan_travel_absence: Produce a structured 3-stage travel prep and care plan.
- search_gardening_knowledge: Look up botanical requirements, companion plants, and pest/mildew remedies.
- get_daylight_and_photoperiod: Fetch real solar daylight hours, sunrise/sunset, and photoperiod classification for the garden.
- list_garden_plants_firestore: Retrieve plants stored in Cloud Firestore.
- geocode_address: Turn an address, city, or postal code into latitude and longitude coordinates.
- find_nearby_places: Find nearby garden centers, nurseries, florists, parks, or supply stores.
"""

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

SYSTEM_INSTRUCTION = schema_manager.generate_system_prompt(
    role_description=BASE_ROLE_DESCRIPTION,
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    model="gemini-2.5-flash",
    name="flora_guide",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        PreloadMemoryTool(),
        tools.get_garden_summary,
        tools.check_local_weather,
        tools.add_or_update_growing_area,
        tools.add_or_update_plant,
        tools.record_plant_observation,
        tools.generate_conditional_care_plan,
        tools.plan_travel_absence,
        tools.list_garden_plants_firestore,
        tools.get_garden_plant_firestore,
        tools.add_or_update_firestore_plant,
        tools.log_firestore_plant_observation,
        tools.search_gardening_knowledge,
        tools.get_daylight_and_photoperiod,
        tools.geocode_address,
        tools.find_nearby_places,
    ],
    code_executor=sandbox_code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

# ADK Application definition
from google.adk.apps import App

app = App(
    name="flora_guide_app",
    root_agent=root_agent,
)
