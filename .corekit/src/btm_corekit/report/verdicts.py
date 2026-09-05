"""Corrective orders: the shape a total rejection returns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One corrective order: where to edit, what to do, and a hint."""

    where: str
    fix: str
    hint: str | None = None

    def view(self) -> dict[str, str]:
        base = {"where": self.where, "fix": self.fix}
        return base | ({"hint": self.hint} if self.hint else {})
