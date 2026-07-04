"""The deterministic agent tool registry the model may call.

Importing this package registers all 11 tools into :data:`TOOL_REGISTRY` (side effect of importing
each tool module in a fixed order). The agent loop consumes :data:`TOOL_REGISTRY` /
:func:`tool_schemas` and constructs a :class:`ToolContext`; it may not call an unregistered tool.
"""

from __future__ import annotations

# Import order fixes the registration order (and thus tool_schemas() order).
from cyclesentinel.tools import (
    brief_tools,
    compute_tools,
    context_tools,
    dose_tool,
    retrieval_tool,
)
from cyclesentinel.tools.base import (
    TOOL_REGISTRY,
    DoseRule,
    ToolContext,
    ToolError,
    ToolRunner,
    ToolSpec,
    get_tool,
    make_tool,
    register,
    tool_schemas,
)
from cyclesentinel.tools.dose_tool import load_dose_rules

# The 11 registered tool names, in registration order (single source of truth for the count).
TOOL_NAMES: tuple[str, ...] = (
    context_tools.get_patient_context.name,
    context_tools.get_trajectory.name,
    compute_tools.tool_compute_e2_rate.name,
    compute_tools.tool_compute_e2_per_follicle.name,
    compute_tools.tool_compute_ohss_composite.name,
    compute_tools.tool_check_progesterone_for_day.name,
    retrieval_tool.retrieve_protocol_rule.name,
    dose_tool.lookup_dose_adjustment.name,
    compute_tools.tool_compute_next_draw_timing.name,
    brief_tools.create_monitoring_brief.name,
    brief_tools.escalate_to_biologist.name,
)

__all__ = [
    "TOOL_NAMES",
    "TOOL_REGISTRY",
    "DoseRule",
    "ToolContext",
    "ToolError",
    "ToolRunner",
    "ToolSpec",
    "get_tool",
    "load_dose_rules",
    "make_tool",
    "register",
    "tool_schemas",
]
