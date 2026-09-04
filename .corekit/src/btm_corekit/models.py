"""Domain records, the refined primitives they share, and the bridge to
corrective orders.

Pattern constraints are safe to use freely: pydantic-core matches with Rust's
linear-time `regex`, so `(a+)+` rejects a 41-char adversarial input in
0.010 ms where Python's `re` would blow up.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, Any, NoReturn, Self, TypeVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
)
from pydantic_core import InitErrorDetails, PydanticCustomError

from btm_corekit.errors import CommandError
from btm_corekit.verdicts import Diagnostic

M = TypeVar("M", bound=BaseModel)
T = TypeVar("T")

HINT = "hint"  # a Diagnostic's hint rides in the pydantic error context


class Model(BaseModel):
    """Frozen so a view cannot mutate the ledger it reads; `extra="forbid"` so
    a typo in a batch is a located fix, not a silently dropped field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    def with_(self, **updates: Any) -> Self:
        """A copy through the validators. `model_copy(update=...)` skips them,
        so a cross-field invariant checked at construction would not survive
        an edit that breaks it."""
        return type(self).model_validate({**self.model_dump(), **updates})


def _folded(raw: Any) -> Any:
    """Normalize before the pattern sees it. `StringConstraints` checks
    `pattern` against the raw input, so `strip_whitespace` and `to_lower`
    alone would reject ` Rent ` against a lowercase pattern."""
    return raw.strip().lower() if isinstance(raw, str) else raw


def _trimmed(raw: Any) -> Any:
    return raw.strip() if isinstance(raw, str) else raw


Folded = BeforeValidator(_folded)
Trimmed = BeforeValidator(_trimmed)

NonEmpty = Annotated[str, Trimmed, StringConstraints(min_length=1)]

Keyword = Annotated[str, Folded, StringConstraints(pattern=r"^[a-z0-9]+$")]

Slug = Annotated[str, Folded, StringConstraints(pattern=r"^[a-z0-9-]+$")]
"""A minted id or any reference to one, the keyword-subset form included."""

Doi = Annotated[str, Folded, StringConstraints(pattern=r"^10\.\d+/\S+$")]
"""A DOI in bare form. The registrant prefix is left open: the registry now
issues longer ones than the classic four digits, and narrowing it here would
silently drop records this library has no reason to reject."""

ArxivId = Annotated[str, Trimmed, StringConstraints(pattern=r"^\d{4}\.\d{4,5}$")]


def _whole(raw: Any) -> Any:
    """`bool` is an `int` in Python and pydantic admits it, so `true` would
    count as one search. A count is a number."""
    if isinstance(raw, bool):
        raise ValueError("write a number, not a boolean")
    return raw


Count = Annotated[int, BeforeValidator(_whole), Field(ge=0)]
"""A non-negative tally: searches run, pages held."""

Positive = Annotated[int, BeforeValidator(_whole), Field(ge=1)]
"""A count that starts at one: a page number, an ordinal."""


def where_of(loc: Sequence[str | int]) -> str:
    """`("objections", 0, "anchors", 1)` becomes `objections[0].anchors[1]`."""
    if not loc:
        return "$"
    head, *rest = loc
    parts = [str(head)]
    parts += [f"[{part}]" if isinstance(part, int) else f".{part}" for part in rest]
    return "".join(parts)


def diagnostics(error: ValidationError) -> list[Diagnostic]:
    """One error in, one corrective order out, in pydantic's order."""
    return [
        Diagnostic(
            where=where_of(item["loc"]),
            fix=item["msg"],
            hint=(item.get("ctx") or {}).get(HINT),
        )
        for item in error.errors()
    ]


def _loc_of(where: str) -> tuple[str | int, ...]:
    if where == "$":
        return ()
    parts = where.replace("[", ".").replace("]", "").split(".")
    return tuple(int(part) if part.isdigit() else part for part in parts)


def parse_with(adapter: TypeAdapter[T], data: Any, what: str) -> T:
    """`parse_model` for a shape no single class names: a discriminated union
    of wire variants, decoded through its adapter."""
    try:
        return adapter.validate_python(data)
    except ValidationError as err:
        problems = "; ".join(f"{d.where}: {d.fix}" for d in diagnostics(err))
        raise CommandError(f"{what}: {problems}") from err


def parse_model(model: type[M], data: Mapping[str, Any], what: str) -> M:
    """Decode into the model, or raise every located problem as one
    `CommandError`. The replay boundary reports a corrupt record through the
    command channel; an escaping `ValidationError` would be a traceback."""
    try:
        return model.model_validate(data)
    except ValidationError as err:
        problems = "; ".join(f"{d.where}: {d.fix}" for d in diagnostics(err))
        raise CommandError(f"{what}: {problems}") from err


def refuse(title: str, problems: Sequence[Diagnostic]) -> NoReturn:
    """Raise every cross-field problem together. A validator that raises
    `ValueError` stops at the first, which costs the agent a round trip per
    problem; the gate's rule is that one rejection carries every fix."""
    raise ValidationError.from_exception_data(
        title,
        [
            InitErrorDetails(
                type=PydanticCustomError(
                    "domain",
                    problem.fix,
                    {HINT: problem.hint} if problem.hint else None,
                ),
                loc=_loc_of(problem.where),
                input=None,
            )
            for problem in problems
        ],
    )


def dump(model: BaseModel) -> dict[str, Any]:
    """A record as it goes to disk: enums by value, absent fields omitted."""
    return model.model_dump(mode="json", exclude_none=True)
