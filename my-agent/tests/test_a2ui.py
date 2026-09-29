import pytest
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.agent import root_agent, SYSTEM_INSTRUCTION
from app.a2ui_utils import a2ui_callback, _extract_a2ui_messages, _wrap_a2ui_part

def test_a2ui_schema_manager_version_and_catalog():
    # Verify A2uiSchemaManager version 0.8 and BasicCatalog
    schema_manager = A2uiSchemaManager(
        version="0.8",
        catalogs=[BasicCatalog.get_config("0.8")],
    )
    prompt = schema_manager.generate_system_prompt(
        role_description="Test agent",
        workflow_description="Test workflow",
        include_schema=True,
        include_examples=True,
    )
    assert len(prompt) > 1000
    assert "beginRendering" in prompt


def test_agent_a2ui_system_instruction():
    # Verify root_agent system instruction contains v0.8 A2UI instructions
    assert "beginRendering" in SYSTEM_INSTRUCTION
    assert "surfaceUpdate" in SYSTEM_INSTRUCTION
    assert "dataModelUpdate" in SYSTEM_INSTRUCTION
    assert "Basic Catalog" in SYSTEM_INSTRUCTION or "Card" in SYSTEM_INSTRUCTION


def test_agent_after_model_callback_wiring():
    # Verify root_agent has a2ui_callback wired
    assert root_agent.after_model_callback is not None
    assert root_agent.after_model_callback == a2ui_callback


def test_a2ui_utils_extraction_and_wrapping():
    sample_a2ui = """[
        {"beginRendering": {"surfaceId": "garden-card", "root": "root-col"}},
        {"surfaceUpdate": {"surfaceId": "garden-card", "components": [{"id": "root-col", "component": {"Column": {"children": []}}}]}}
    ]"""
    messages = _extract_a2ui_messages(sample_a2ui)
    assert len(messages) == 2
    assert "beginRendering" in messages[0]
    assert "surfaceUpdate" in messages[1]

    part = _wrap_a2ui_part(messages[0])
    assert b"<a2a_datapart_json>" in part.inline_data.data
    assert b"beginRendering" in part.inline_data.data
