"""
Tests for Memory Bank allergy configuration and agent memory wiring.
"""

import pytest
from app.agent import root_agent, BASE_ROLE_DESCRIPTION, SYSTEM_INSTRUCTION
from google.adk.tools.preload_memory_tool import PreloadMemoryTool


def test_agent_allergy_principles_in_instruction():
    """Verify that allergy safety and cross-session memory principles are in the agent instructions."""
    assert "Allergy Safety & Cross-Session Memory" in BASE_ROLE_DESCRIPTION
    assert "allergies" in BASE_ROLE_DESCRIPTION.lower()
    assert "sensitivities" in BASE_ROLE_DESCRIPTION.lower()
    assert "hypoallergenic" in BASE_ROLE_DESCRIPTION.lower()


def test_preload_memory_tool_configured():
    """Verify that PreloadMemoryTool is in the root agent tools."""
    tool_classes = [t.__class__ for t in root_agent.tools]
    assert PreloadMemoryTool in tool_classes


def test_after_agent_callback_saves_memory():
    """Verify that generate_memories_callback is registered as after_agent_callback."""
    assert root_agent.after_agent_callback is not None
    assert root_agent.after_agent_callback.__name__ == "generate_memories_callback"


def test_agent_engine_memory_bank_allergy_topic():
    """Verify that Agent Engine 4973600716070322176 has the user_allergies custom topic."""
    import agentplatform
    client = agentplatform.Client(project="qwiklabs-gcp-04-c7b2618a365a", location="us-central1")
    ae = client.agent_engines.get(
        name="projects/1536983767/locations/us-central1/reasoningEngines/4973600716070322176"
    )
    custom_configs = ae.api_resource.context_spec.memory_bank_config.customization_configs
    assert len(custom_configs) > 0

    topics = custom_configs[0].memory_topics
    allergy_topics = [
        t.custom_memory_topic for t in topics
        if t.custom_memory_topic and t.custom_memory_topic.label == "user_allergies"
    ]
    assert len(allergy_topics) == 1
    assert "allergies" in allergy_topics[0].description.lower()
    assert "sensitivities" in allergy_topics[0].description.lower()

    # Verify few-shot examples for allergies are present
    examples = custom_configs[0].generate_memories_examples
    assert examples is not None and len(examples) >= 3
    allergy_example_memories = [
        m for ex in examples for m in ex.generated_memories
        if any(topic.custom_memory_topic_label == "user_allergies" for topic in (m.topics or []))
    ]
    assert len(allergy_example_memories) >= 3
