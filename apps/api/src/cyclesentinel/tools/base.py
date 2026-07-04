"""Tool registry core: :class:`ToolSpec`, :class:`ToolContext`, and the registration mechanism.

Every deterministic tool the model may call is a :class:`ToolSpec` — a name + description, a
Pydantic ``args_model`` (so malformed calls raise ``ValidationError`` before any side effect), a
Pydantic ``result_model``, and an ``async`` ``run`` coroutine. Tools self-register into the module
``TOOL_REGISTRY`` at import time; the agent loop never invents a tool that is not in the registry.

``tool_schemas()`` renders the registry to the JSON-Schema ``ToolSchema`` list the LLM is given.
:class:`ToolContext` is the injected dependency bundle every ``run`` receives (db session,
retriever, cited thresholds/dose tables, corpus, and deterministic ``IdFactory`` / ``Clock``).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from cyclesentinel.calculators import Thresholds
from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import Clock, IdFactory, ToolSchema, VisualRetriever

if TYPE_CHECKING:  # avoid importing SQLAlchemy / corpus at import time where unneeded
    from sqlalchemy.orm import Session

    from cyclesentinel.retrieval.corpus import Corpus


class ToolError(RuntimeError):
    """Raised when a tool cannot run against current state (e.g. an unknown patient id).

    Distinct from a Pydantic ``ValidationError`` (malformed *arguments*): a ``ToolError`` means the
    arguments were well-formed but the referenced data does not exist / cannot be computed.
    """


@dataclass(frozen=True)
class DoseRule:
    """One gonadotropin dose-adjustment row from ``dose_tables.json``.

    Read by ``lookup_dose_adjustment``. ``delta_iu_range`` is an inclusive ``(low, high)`` IU range,
    or ``None`` when the situation calls for a non-numeric action (e.g. ``freeze_all_consider``).
    The citation fields ground the advice to a protocol page.
    """

    situation: str
    action: str
    delta_iu_range: tuple[int, int] | None
    doc_id: str
    rule_type: RuleType
    page: int
    article: str


@dataclass
class ToolContext:
    """The dependency bundle injected into every tool ``run``.

    ``thresholds`` is the :class:`~cyclesentinel.calculators.Thresholds` TypedDict shape the
    calculators consume (not the calculator-keyed ``thresholds.json`` on disk). ``ids`` / ``clock``
    are the deterministic id/timestamp sources so a run is byte-reproducible under replay.
    """

    session: Session
    retriever: VisualRetriever
    thresholds: Thresholds
    dose_table: Mapping[str, DoseRule]
    corpus: Corpus | None = None
    ids: IdFactory = field(default_factory=lambda: IdFactory("id"))
    clock: Clock = field(default_factory=lambda: Clock(datetime(2026, 1, 1, tzinfo=UTC)))


# The concrete runner stored on a ToolSpec: takes a *base* model (narrowed inside) and returns one.
ToolRunner = Callable[["ToolContext", BaseModel], Awaitable[BaseModel]]


@dataclass(frozen=True)
class ToolSpec:
    """A single registered tool: its name, description, Pydantic arg/result models, and runner."""

    name: str
    description: str
    args_model: type[BaseModel]
    result_model: type[BaseModel]
    run: ToolRunner

    async def invoke(self, ctx: ToolContext, raw_args: Mapping[str, object]) -> BaseModel:
        """Validate ``raw_args`` against ``args_model`` (raising ``ValidationError``) then run."""
        args = self.args_model.model_validate(dict(raw_args))
        return await self.run(ctx, args)

    def schema(self) -> ToolSchema:
        """Render this tool to the JSON-Schema ``ToolSchema`` the LLM sees."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.args_model.model_json_schema(),
        )


def _bind[ArgsT: BaseModel, ResultT: BaseModel](
    args_model: type[ArgsT],
    fn: Callable[[ToolContext, ArgsT], Awaitable[ResultT]],
) -> ToolRunner:
    """Adapt a type-specific tool function to the erased :data:`ToolRunner` signature.

    The ``isinstance`` check narrows the erased ``BaseModel`` back to the concrete ``ArgsT`` for the
    type checker; at runtime it always holds because :meth:`ToolSpec.invoke` validated the argument
    through ``args_model`` first.
    """

    async def runner(ctx: ToolContext, args: BaseModel) -> BaseModel:
        if not isinstance(args, args_model):  # pragma: no cover - invoke() guarantees the type
            raise ToolError(f"expected {args_model.__name__}, got {type(args).__name__}")
        return await fn(ctx, args)

    return runner


TOOL_REGISTRY: dict[str, ToolSpec] = {}


def make_tool[ArgsT: BaseModel, ResultT: BaseModel](
    *,
    name: str,
    description: str,
    args_model: type[ArgsT],
    result_model: type[ResultT],
    fn: Callable[[ToolContext, ArgsT], Awaitable[ResultT]],
) -> ToolSpec:
    """Build a :class:`ToolSpec`, wrapping ``fn`` so its arg type is validated + narrowed."""
    return ToolSpec(
        name=name,
        description=description,
        args_model=args_model,
        result_model=result_model,
        run=_bind(args_model, fn),
    )


def register(spec: ToolSpec) -> ToolSpec:
    """Register ``spec`` under its name (rejecting duplicates) and return it."""
    if spec.name in TOOL_REGISTRY:
        raise ValueError(f"tool already registered: {spec.name!r}")
    TOOL_REGISTRY[spec.name] = spec
    return spec


def get_tool(name: str) -> ToolSpec:
    """Return the registered tool named ``name`` or raise ``KeyError`` (never an unknown one)."""
    return TOOL_REGISTRY[name]


def tool_schemas() -> list[ToolSchema]:
    """Return each registered tool's :class:`ToolSchema`, in registration order (JSON-safe)."""
    return [spec.schema() for spec in TOOL_REGISTRY.values()]
