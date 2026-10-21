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
    Chain,
    CritiqueEntry,
    DecisionEntry,
    FillEntry,
    HoldingsEntry,
    HypothesisEntry,
    Preferences,
    RegimeEntry,
    ScoredEntry,
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
    '"falsifier_by": "YYYY-MM-DD", "counterparty": "...", '
    '"min_holding_days": 21, "odds": {"p_win": 0.55, "payoff": 1.5, '
    '"horizon_days": 63, "kelly_implied": 0.25} (optional at registration, '
    "required before check reads promotable or probe; kelly_implied is p_win "
    '- (1 - p_win) / payoff within 0.01), "mechanism": "..." (optional), '
    '"sector": "..." (optional), "supersedes": "<id>" (optional; spends a '
    "trial of its family), "
    f'"chain": "{_choices(Chain)}", "expectation_source": "...", '
    '"discounted": "...", "confidence": 0.4 (these four optional; critique '
    "flags each one absent when limits.families.<family_id>.event is true)}",
    "critiques": '{"kw": ["two", "words"], "run_id": "<run id>", '
    '"blockers": ["..."], "concerns": ["..."], "by": "<delegate>", '
    '"confidence": 0.6 (optional)}',
    "decisions": '{"kw": ["two", "words"], "subject": "<strategy, run id, '
    f'hypothesis id, or proposal date>", "action": "{_choices(Action)}", '
    '"reason": "...", "odds": {"p_win": 0.55, "payoff": 1.5, '
    '"horizon_days": 63, "kelly_implied": 0.25} (optional), "confidence": 0.6 '
    '(optional), "supersedes": "<id>" (optional); forgo names a strategy}',
    "scored": '{"kw": ["two", "words"], "subject": "<live hypothesis id>", '
    '"resolved": "YYYY-MM-DD", "outcome": "...", "realized_return": 0.04, '
    '"brier": 0.2 (0 to 1), "log_score": -0.5 (at most 0), "attribution": '
    '{"market": 0.01, "factor": 0.02, "currency": 0.0, "idiosyncratic": 0.015, '
    '"costs": -0.005}, "supersedes": "<scored id>" (optional)}',
    "regimes": '{"kw": ["two", "words"], "as_of": "YYYY-MM-DD", '
    '"confidence": 0.6, '
    f'"falsified": ["{_choices(c for c in Chain if c is not Chain.NONE)}"] '
    '(optional), "supersedes": "<live regime id>" (optional); suggested free '
    'fields, never checked: "short_cycle": "easing|mid-expansion|'
    'late-expansion|tightening|contraction", "long_cycle": "early|bubble|top|'
    'depression|deleveraging|normalization", "bubble_count": {"count": 2, '
    '"evidence": ["one per item present"]}, "policy_mix": '
    '["austerity|defaults|transfers|printing"], "other_forces": '
    '{"internal_order": "...", "external_order": "...", "nature": "...", '
    '"technology": "..."}, "observables": {"<name>": {"value": "...", '
    '"as_of": "YYYY-MM-DD", "source": "<url>"}}}',
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
    scored: Rows = ()
    regimes: Rows = ()
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
    live_regimes: frozenset[str] = frozenset()
    live_hypotheses: frozenset[str] = frozenset()


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
            for kind in (
                Kind.HYPOTHESIS,
                Kind.CRITIQUE,
                Kind.DECISION,
                Kind.SCORED,
                Kind.REGIME,
            )
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
                    "measure will refuse it"
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
            if (
                subject is not None
                and entry.action is Action.FORGO
                and subject not in self.context.strategies
            ):
                self.fail(
                    f"{where}.subject",
                    f"replace '{subject}': forgo names a strategy",
                    "valid: " + ", ".join(sorted(self.context.strategies)),
                )
                subject = None
            full = self.named(Kind.DECISION, entry, where, entry.supersedes)
            if full is not None and subject is not None:
                self.stage(Kind.DECISION, full, {**dump(entry), "subject": subject})

    def take_scored(self, rows: Rows) -> None:
        """`subject` names a live hypothesis: on file and not superseded, or
        made earlier in this batch."""
        made = self.pools[Kind.HYPOTHESIS].fresh
        replaced = {
            row.get("supersedes") for row in self.staged.get(Kind.HYPOTHESIS, [])
        }
        live = Pool(
            "live hypothesis",
            sorted((self.context.live_hypotheses | made) - replaced),
        )
        for index, row in enumerate(rows):
            where = f"scored[{index}]"
            if not self.envelope_free(row, where):
                continue
            entry = self.decode(ScoredEntry, row, where, SCHEMA["scored"])
            if entry is None:
                continue
            subject = self.resolve_ref(entry.subject, live, f"{where}.subject")
            full = self.named(Kind.SCORED, entry, where, entry.supersedes)
            if full is not None and subject is not None:
                self.stage(Kind.SCORED, full, {**dump(entry), "subject": subject})

    def take_regimes(self, rows: Rows) -> None:
        for index, row in enumerate(rows):
            where = f"regimes[{index}]"
            if not self.envelope_free(row, where):
                continue
            entry = self.decode(RegimeEntry, row, where, SCHEMA["regimes"])
            if entry is None:
                continue
            self.bubble_advisory(row.get("bubble_count"), where)
            live = self.live_regime(entry.supersedes, where)
            full = self.named(Kind.REGIME, entry, where, entry.supersedes)
            if full is not None and live:
                self.stage(Kind.REGIME, full, dump(entry))

    def live_regime(self, target: str | None, where: str) -> bool:
        """A regime correction replaces a live line, never one already replaced;
        an unknown id is `supersedes`'s own refusal."""
        known = target in self.context.ids.get(Kind.REGIME, [])
        if not known or target in self.context.live_regimes:
            return True
        self.fail(
            f"{where}.supersedes",
            f"replace '{target}': a later regime line already supersedes it",
            "supersede the live regime line, in full",
        )
        return False

    def bubble_advisory(self, bubble: object, where: str) -> None:
        """Suggested shape only: count against evidence lines; never refuses."""
        if not isinstance(bubble, dict):
            return
        count, evidence = bubble.get("count"), bubble.get("evidence")
        listed = len(evidence) if isinstance(evidence, list) else None
        if isinstance(count, int) and listed is not None and listed != count:
            self.advisories.append(
                f"{where}.bubble_count: count {count} but {listed} "
                "evidence line(s); give one per item present"
            )

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
    Order: hypotheses, critiques, decisions, scored, regimes, fills,
    holdings, preferences, so a later kind may name a hypothesis made
    earlier."""
    expansion = _Expansion(context, maker, stamp)
    expansion.known_keys(batch, RecordBatch)
    record = expansion.families(batch, RecordBatch, SCHEMA)
    expansion.take_hypotheses(record.hypotheses)
    expansion.take_critiques(record.critiques)
    expansion.take_decisions(record.decisions)
    expansion.take_scored(record.scored)
    expansion.take_regimes(record.regimes)
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
            "scored": pools[Kind.SCORED].new,
            "regimes": pools[Kind.REGIME].new,
            "fills": fills,
            "holdings": opening,
        },
        advisories=expansion.advisories,
        problems=expansion.problems,
    )
