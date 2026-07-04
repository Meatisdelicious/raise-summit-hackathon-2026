"""The registry has exactly the 11 named tools; schemas are JSON-serializable; args validated."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from cyclesentinel.inference.base import ToolSchema
from cyclesentinel.tools import TOOL_NAMES, TOOL_REGISTRY, get_tool, tool_schemas

EXPECTED_NAMES = {
    "get_patient_context",
    "get_trajectory",
    "compute_e2_rate",
    "compute_e2_per_follicle",
    "compute_ohss_composite",
    "check_progesterone_for_day",
    "retrieve_protocol_rule",
    "lookup_dose_adjustment",
    "compute_next_draw_timing",
    "create_monitoring_brief",
    "escalate_to_biologist",
}


def test_registry_has_exactly_the_eleven_named_tools() -> None:
    assert len(TOOL_REGISTRY) == 11
    assert set(TOOL_REGISTRY) == EXPECTED_NAMES
    assert set(TOOL_NAMES) == EXPECTED_NAMES
    assert len(TOOL_NAMES) == 11  # no dupes
    # every registered spec is keyed under its own name
    for name, spec in TOOL_REGISTRY.items():
        assert spec.name == name


def test_tool_schemas_are_json_serializable_and_well_formed() -> None:
    schemas = tool_schemas()
    assert len(schemas) == 11
    assert {s.name for s in schemas} == EXPECTED_NAMES  # every tool exposes a schema
    for schema in schemas:
        assert isinstance(schema, ToolSchema)
        # both the ToolSchema payload and its OpenAI wire form must round-trip through JSON
        json.dumps(schema.parameters)
        json.dumps(schema.to_wire())
        assert schema.parameters["type"] == "object"
        assert schema.description


def test_get_tool_rejects_unknown_names() -> None:
    with pytest.raises(KeyError):
        get_tool("definitely_not_a_registered_tool")


@pytest.mark.parametrize(
    ("tool_name", "bad_args"),
    [
        ("get_patient_context", {}),  # missing patient_id
        ("compute_e2_per_follicle", {"result_id": 123}),  # wrong type is coerced? no: int != str
        ("compute_ohss_composite", {"patient_id": "p"}),  # missing result_id
        ("retrieve_protocol_rule", {"query": "q", "rule_type": "not_a_rule"}),  # bad enum
        ("retrieve_protocol_rule", {"query": "q", "rule_type": "ohss", "top_k": 0}),  # ge=1
        ("lookup_dose_adjustment", {"situation": "nonsense"}),  # bad literal
        ("escalate_to_biologist", {"level": "screaming"}),  # bad enum
        ("create_monitoring_brief", {"patient_id": "p"}),  # missing required fields
    ],
)
def test_tools_reject_malformed_args(tool_name: str, bad_args: dict[str, object]) -> None:
    spec = get_tool(tool_name)
    with pytest.raises(ValidationError):
        spec.args_model.model_validate(bad_args)


@pytest.mark.parametrize(
    ("tool_name", "good_args"),
    [
        ("get_patient_context", {"patient_id": "pat_t"}),
        ("get_trajectory", {"patient_id": "pat_t"}),
        ("compute_e2_rate", {"patient_id": "pat_t"}),
        ("compute_e2_per_follicle", {"result_id": "res_t2"}),
        ("compute_ohss_composite", {"patient_id": "pat_t", "result_id": "res_t2"}),
        ("check_progesterone_for_day", {"result_id": "res_t2"}),
        ("retrieve_protocol_rule", {"query": "q", "rule_type": "ohss"}),
        ("lookup_dose_adjustment", {"situation": "ohss_risk"}),
        ("compute_next_draw_timing", {"patient_id": "pat_t"}),
        ("escalate_to_biologist", {"level": "urgent"}),
    ],
)
def test_tools_accept_valid_args(tool_name: str, good_args: dict[str, object]) -> None:
    spec = get_tool(tool_name)
    model = spec.args_model.model_validate(good_args)
    assert isinstance(model, spec.args_model)
