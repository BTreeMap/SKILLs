"""Domain records, the refined primitives they share, and the bridge to
corrective orders.

Pattern constraints are safe to use freely: pydantic-core matches with Rust's
linear-time `regex`, so `(a+)+` rejects a 41-char adversarial input in
0.010 ms where Python's `re` would blow up.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any, NoReturn

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StringConstraints,
    ValidationError,
)
from pydantic_core import InitErrorDetails, PydanticCustomError

from btm_corekit.verdicts import Diagnostic

HINT = "hint"  # a Diagnostic's hint rides in the pydantic error context


class Model(BaseModel):
    """Frozen so a view cannot mutate the ledger it reads; `extra="forbid"` so
    a typo in a batch is a located fix, not a silently dropped field."""

    model_config = ConfigDict(frozen=True, extra="forbid")


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

Doi = Annotated[str, Folded, StringConstraints(pattern=r"^10\.\d{4,9}/\S+$")]

ArxivId = Annotated[str, Trimmed, StringConstraints(pattern=r"^\d{4}\.\d{4,5}$")]


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
