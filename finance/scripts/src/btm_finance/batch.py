"""The record gate, pure: decode, resolve, stage; a rejection lists every fix.

Nothing here writes. The caller commits the staged rows only when the
problem list comes back empty, so a rejected batch leaves the book as it was.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import ConfigDict

from btm_corekit import Acceptance, Diagnostic, Model, Named, Pool, dump
from btm_finance.ledger import ENVELOPE, Kind, Row
from btm_finance.models import (
    Action,
    Cadence,
    CapacityClass,
    CritiqueEntry,
    DecisionEntry,
    FillEntry,
    HoldingsEntry,
    HypothesisEntry,
    Preferences,
    Side,
)

Maker = Callable[[Iterable[str]], str]
Rows = tuple[Mapping[str, Any], ...]


def _choices(vocabulary: Iterable[str]) -> str:
    return "|".join(vocabulary)


SCHEMA: dict[str, str] = {
    "hypotheses": '{"kw": ["two", "words"], "strategy": "<name>", '
    '"family_id": "<key of limits.families>", '
    f'"capacity_class": "{_choices(CapacityClass)}", "falsifier": "...", '
    '"counterparty": "...", "min_holding_days": 21, "mechanism": "..." '
    '(optional), "sector": "..." (optional), "supersedes": "<id>" (optional)}',
    "critiques": '{"kw": ["two", "words"], "run_id": "<run id>", '
    '"blockers": ["..."], "concerns": ["..."], "by": "<delegate>"}',
    "decisions": '{"kw": ["two", "words"], "subject": "<strategy, run id, '
    f'hypothesis id, or proposal date>", "action": "{_choices(Action)}", '
    '"reason": "...", "supersedes": "<id>" (optional)}',
    "fills": '{"symbol": "...", '
    f'"side": "{_choices(Side)}", "quantity": 10, "price": 12.5, '
    '"date": "YYYY-MM-DD", "strategy": "<name>|opening", "dry_run": false}',
    "holdings": '{"date": "YYYY-MM-DD", "positions": [{"symbol": "...", '
    '"quantity": 10, "cost_basis": 12.5 (optional, per share)}]}',
    "preferences": '{"focus_sectors": ["..."], "exclusions": {"symbols": [], '
    f'"sectors": [], "countries": []}}, "cadence": "{_choices(Cadence)}"}}',
}


class RecordBatch(Model):
    """The container: rows stay opaque and decode one at a time, so one bad
    row never hides its neighbours' problems."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    hypotheses: Rows = ()
    critiques: Rows = ()
    decisions: Rows = ()
    fills: Rows = ()
    holdings: Rows = ()
    preferences: Rows = ()


BATCH_KEYS = tuple(RecordBatch.model_fields)


@dataclass(frozen=True, slots=True)
class Context:
    """Live book state the gate resolves references against."""

    families: frozenset[str]
    min_holding_days: int
    ids: Mapping[Kind, list[str]]
    strategies: list[str]
    proposals: list[str]


@dataclass(slots=True)
class RecordResult:
    staged: dict[Kind, list[Row]] = field(default_factory=dict)
    preferences: Preferences | None = None
    new: dict[str, Any] = field(default_factory=dict)
    advisories: list[str] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)


class _Expansion(Acceptance):
    """One batch through the phases; every method appends, none raises."""

    def __init__(self, context: Context, maker: Maker, stamp: str) -> None:
        super().__init__(maker)
        self.maker_of = maker
        self.context = context
        self.stamp = stamp
        self.staged: dict[Kind, list[Row]] = {}
        self.pools = {
            kind: Pool(kind.value, list(context.ids.get(kind, [])))
            for kind in (Kind.HYPOTHESIS, Kind.CRITIQUE, Kind.DECISION)
        }

    def stage(self, kind: Kind, full: str, body: Mapping[str, Any]) -> None:
        self.staged.setdefault(kind, []).append({"id": full, "ts": self.stamp, **body})

    def envelope_free(self, row: Mapping[str, Any], where: str) -> bool:
        taken = sorted(set(row) & set(ENVELOPE))
        for key in taken:
            self.fail(f"{where}.{key}", f"remove '{key}': the ledger stamps it")
        return not taken

    def supersedes(self, kind: Kind, target: str | None, where: str) -> bool:
        if target is None or target in self.context.ids.get(kind, []):
            return True
        self.fail(
            f"{where}.supersedes",
            f"replace '{target}': no {kind.value} line holds that id",
            "supersedes names an existing id of the same kind, in full",
        )
        return False

    def named(
        self, kind: Kind, entry: Named, where: str, supersedes: str | None
    ) -> str | None:
        target_ok = self.supersedes(kind, supersedes, where)
        full = self.make_id(entry, self.pools[kind], where)
        return full if target_ok else None

    def take_hypotheses(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"hypotheses[{index}]"
            if not self.envelope_free(row, where):
                continue
            entry = self.decode(HypothesisEntry, row, where, SCHEMA["hypotheses"])
            if entry is None:
                continue
            family_ok = entry.family_id in self.context.families
            if not family_ok:
                self.fail(
                    f"{where}.family_id",
                    f"replace '{entry.family_id}': limits.families has no such key",
                    "valid: "
                    + ", ".join(sorted(self.context.families))
                    + "; the human adds families to limits.json",
                )
            if entry.min_holding_days < self.context.min_holding_days:
                self.advisories.append(
                    f"{where}: min_holding_days {entry.min_holding_days} is under "
                    f"limits.min_holding_days {self.context.min_holding_days}; "
                    "scoring will refuse it"
                )
            if entry.strategy not in self.context.strategies:
                self.advisories.append(
                    f"{where}: strategies/{entry.strategy}/ does not exist yet"
                )
            full = self.named(Kind.HYPOTHESIS, entry, where, entry.supersedes)
            if full is not None and family_ok:
                self.stage(Kind.HYPOTHESIS, full, dump(entry))

    def take_critiques(self, rows: Rows) -> None:
        runs = self.context.ids.get(Kind.RUN, [])
        pool = Pool("run", list(runs))
        for index, row in enumerate(rows):
            where = f"critiques[{index}]"
            if not self.envelope_free(row, where):
                continue
            entry = self.decode(CritiqueEntry, row, where, SCHEMA["critiques"])
            if entry is None:
                continue
            if runs:
                run_id = self.resolve_ref(entry.run_id, pool, f"{where}.run_id")
            else:
                run_id = None
                self.fail(
                    f"{where}.run_id",
                    f"replace '{entry.run_id}': the book holds no run yet",
                    "critique a run_id a runs file holds",
                )
            full = self.named(Kind.CRITIQUE, entry, where, entry.supersedes)
            if full is not None and run_id is not None:
                self.stage(Kind.CRITIQUE, full, {**dump(entry), "run_id": run_id})

    def take_decisions(self, rows: Rows) -> None:
        subjects = Pool(
            "subject",
            [
                *self.context.strategies,
                *self.context.ids.get(Kind.RUN, []),
                *self.pools[Kind.HYPOTHESIS].ids,
                *self.context.proposals,
            ],
        )
        for index, row in enumerate(rows):
            where = f"decisions[{index}]"
            if not self.envelope_free(row, where):
                continue
            entry = self.decode(DecisionEntry, row, where, SCHEMA["decisions"])
            if entry is None:
                continue
            subject = self.resolve_ref(entry.subject, subjects, f"{where}.subject")
            full = self.named(Kind.DECISION, entry, where, entry.supersedes)
            if full is not None and subject is not None:
                self.stage(Kind.DECISION, full, {**dump(entry), "subject": subject})

    def take_fills(self, rows: Rows) -> list[str]:
        made: list[str] = []
        for index, row in enumerate(rows):
            where = f"fills[{index}]"
            if not self.envelope_free(row, where):
                continue
            entry = self.decode(FillEntry, row, where, SCHEMA["fills"])
            if entry is None or not self.supersedes(Kind.FILL, entry.supersedes, where):
                continue
            full = self.maker_of([entry.symbol, entry.side])
            self.stage(Kind.FILL, full, dump(entry))
            made.append(full)
        return made

    def take_holdings(self, rows: Rows) -> list[str]:
        """Each position becomes an opening buy fill dated as the holdings."""
        made: list[str] = []
        for index, row in enumerate(rows):
            where = f"holdings[{index}]"
            entry = self.decode(HoldingsEntry, row, where, SCHEMA["holdings"])
            if entry is None:
                continue
            for position in entry.positions:
                if position.cost_basis is None:
                    self.advisories.append(
                        f"{where}: {position.symbol} has no cost_basis; price null"
                    )
                extras = {
                    key: value
                    for key, value in dump(position).items()
                    if key not in {"cost_basis", *ENVELOPE}
                }
                full = self.maker_of(["opening", position.symbol])
                self.stage(
                    Kind.FILL,
                    full,
                    {
                        **extras,
                        "side": "buy",
                        "price": position.cost_basis,
                        "date": entry.date.isoformat(),
                        "strategy": "opening",
                        "dry_run": False,
                        "holdings": True,
                    },
                )
                made.append(full)
        return made

    def take_preferences(self, rows: Rows) -> Preferences | None:
        if len(rows) > 1:
            self.fail(
                "preferences",
                "send one preferences entry: it rewrites preferences.json whole",
            )
            return None
        if not rows:
            return None
        return self.decode(
            Preferences, rows[0], "preferences[0]", SCHEMA["preferences"]
        )


def expand_batch(
    context: Context, batch: Mapping[str, Any], maker: Maker, stamp: str
) -> RecordResult:
    """Every row decoded, resolved, and staged, or every problem located.
    Order: hypotheses, critiques, decisions, fills, holdings, preferences, so
    a decision may name a hypothesis made earlier in the same batch."""
    expansion = _Expansion(context, maker, stamp)
    expansion.known_keys(batch, RecordBatch)
    record = expansion.families(batch, RecordBatch, SCHEMA)
    expansion.take_hypotheses(record.hypotheses)
    expansion.take_critiques(record.critiques)
    expansion.take_decisions(record.decisions)
    fills = expansion.take_fills(record.fills)
    opening = expansion.take_holdings(record.holdings)
    preferences = expansion.take_preferences(record.preferences)
    if not expansion.staged and preferences is None and expansion.clean:
        expansion.fail("$", "add at least one entry: the batch records nothing")
    pools = expansion.pools
    return RecordResult(
        staged=expansion.staged,
        preferences=preferences,
        new={
            "hypotheses": pools[Kind.HYPOTHESIS].new,
            "critiques": pools[Kind.CRITIQUE].new,
            "decisions": pools[Kind.DECISION].new,
            "fills": fills,
            "holdings": opening,
        },
        advisories=expansion.advisories,
        problems=expansion.problems,
    )
