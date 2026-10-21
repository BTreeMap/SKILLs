"""Book-root instructions from the operator's answers: `README.md` for
humans, `AGENTS.md` for agents, `CLAUDE.md` pointing at it; and the warnings
bare `check` derives from them."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any

from pydantic import BaseModel

from btm_corekit import CommandError, parse_model, signal, write_atomic
from btm_finance.models import Answers, Limits, Preferences, RunDays

README, AGENTS, CLAUDE = "README.md", "AGENTS.md", "CLAUDE.md"
FILES = (README, AGENTS, CLAUDE)
FALLBACK = "Read AGENTS.md.\n"
INVARIANTS = "## Invariants"
DEFAULT_CAP = 10_000_000
DEFAULTED = " (default)"


def answers_of(raw: str) -> Answers:
    """The answers slot decoded; a key outside the shape refuses (no secrets)."""
    try:
        data = json.loads(raw)
    except ValueError as err:
        raise CommandError(f"make the answers valid JSON: {err}") from err
    if not isinstance(data, dict):
        raise CommandError(
            "the answers are one JSON object; check --schema answers prints it"
        )
    return parse_model(Answers, data, "the answers")


def section(text: str, heading: str = INVARIANTS) -> str | None:
    """`heading` through the line before the next `## ` heading; None when
    absent. O(len(text))."""
    _, found, rest = ("\n" + text).partition(f"\n{heading}\n")
    if not found:
        return None
    body, _, _ = rest.partition("\n## ")
    return f"{heading}\n{body.rstrip()}"


@dataclass(frozen=True, slots=True)
class Setting:
    """Book facts the templates read beside the answers."""

    title: str
    dated: str
    cap: int
    held_out: str
    universe: bool
    binding: str


def cell(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())


def given(model: BaseModel, field: str, text: str) -> str:
    """`text`, marked `(default)` when the operator left `field` out."""
    return text if field in model.model_fields_set else text + DEFAULTED


def listed(values: tuple[Any, ...], empty: str) -> str:
    return ", ".join(map(str, values)) if values else empty


LOCALE = "operator's locale"
CUTOFF = "agent's stated cutoff; unset"


def joined(*parts: str) -> str:
    return "; ".join(parts)


def answer_rows(answers: Answers, setting: Setting) -> list[tuple[str, str]]:
    """One row per question, in question order."""
    broker, capital, risk = answers.broker, answers.capital, answers.risk
    horizon, universe, sources = answers.horizon, answers.universe, answers.sources
    out = universe.exclusions
    accounts = ", ".join(f"{a.name} ({a.kind.value})" for a in broker.accounts)
    api = "API" if broker.api else "no API: check prints orders for hand entry"
    people = "; ".join(
        f"{c.name} ({c.kind.value}, {'may' if c.may_propose else 'may not'} propose)"
        for c in answers.collaborators
    )
    named = universe.index or ("universe.csv" if setting.universe else "none given")
    used = listed(tuple(source.value for source in sources.used), "none")
    excluded = (
        f"excluded symbols {listed(out.symbols, 'none')}, sectors "
        f"{listed(out.sectors, 'none')}, countries {listed(out.countries, 'none')}"
    )
    return [
        (
            "1. Jurisdiction, currency",
            joined(
                given(answers, "jurisdiction", answers.jurisdiction or LOCALE),
                given(answers, "currency", answers.currency or LOCALE),
            ),
        ),
        (
            "2. Broker, accounts",
            joined(
                given(broker, "name", broker.name or "unnamed"),
                "accounts " + given(broker, "accounts", accounts or "unnamed"),
                "sleeves trade in "
                + given(broker, "sleeve_account", broker.sleeve_account or "unnamed"),
                given(broker, "api", api),
            ),
        ),
        (
            "3. Capital",
            joined(
                "now " + given(capital, "now", str(setting.cap)),
                "in six months "
                + given(capital, "six_months", str(capital.six_months or "not given")),
            ),
        ),
        (
            "4. Risk",
            joined(
                "ruin_bound " + given(risk, "ruin_bound", str(risk.ruin_bound)),
                "Kelly backtest "
                + given(risk, "kelly_backtest", str(risk.kelly_backtest)),
            ),
        ),
        (
            "5. Horizon, cadence",
            joined(
                "holding " + given(horizon, "holding", horizon.holding),
                "rebalance " + given(horizon, "cadence", horizon.cadence.value),
                "brief at " + given(horizon, "brief_hour", hour(horizon.brief_hour)),
                given(horizon, "schedule", horizon.schedule.value),
            ),
        ),
        (
            "6. Universe",
            joined(
                given(universe, "index", named),
                "exchanges "
                + given(universe, "exchanges", listed(universe.exchanges, "any")),
                "cap ceiling "
                + given(universe, "cap_ceiling", str(universe.cap_ceiling or "none")),
                given(universe, "exclusions", excluded),
                "focus "
                + given(
                    universe, "focus_sectors", listed(universe.focus_sectors, "none")
                ),
            ),
        ),
        (
            "7. Sources",
            joined(
                given(sources, "used", used),
                "EDGAR contact "
                + given(sources, "edgar_contact", sources.edgar_contact or "none"),
                "keys in environment only",
            ),
        ),
        (
            "8. model_cutoff",
            given(answers, "model_cutoff", str(answers.model_cutoff or CUTOFF)),
        ),
        ("9. Held-out path", given(answers, "held_out", setting.held_out)),
        (
            "10. Collaborators",
            given(answers, "collaborators", people or "operator only"),
        ),
    ]


def hour(value: int) -> str:
    return f"{value:02d}:00"


def when(answers: Answers) -> str:
    """When the brief arrives, in words: `07:00 on weekdays`."""
    days = "every day" if answers.horizon.schedule is RunDays.DAILY else "on weekdays"
    return f"{hour(answers.horizon.brief_hour)} {days}"


def sending(answers: Answers) -> str:
    broker = answers.broker.name or "your broker"
    if answers.broker.api:
        return (
            f"{broker} has an API, but this book never calls it and holds no "
            "password or key for it. You enter every order yourself."
        )
    return f"You enter every order yourself at {broker}."


def collaborators(answers: Answers) -> str:
    if not answers.collaborators:
        return "Operator alone works here and decides; agent proposes to operator."
    who = "; ".join(
        f"{c.name} ({c.kind.value}) {'may' if c.may_propose else 'may not'} propose"
        for c in answers.collaborators
    )
    return f"Also in this book: {who}. Operator alone decides."


def readme(template: str, answers: Answers, setting: Setting) -> str:
    """For a person who never reads the skill: no command, flag, or path but
    `ledger/`."""
    account = answers.broker.sleeve_account
    return Template(template).substitute(
        title=setting.title,
        holding=answers.horizon.holding,
        when=when(answers),
        sending=sending(answers),
        account=f" Orders for this book go to account {account}." if account else "",
    )


def agents(template: str, answers: Answers, setting: Setting) -> str:
    rows = "\n".join(
        f"| {cell(q)} | {cell(a)} |" for q, a in answer_rows(answers, setting)
    )
    return Template(template).substitute(
        title=setting.title,
        binding=setting.binding,
        holding=answers.horizon.holding,
        cadence=answers.horizon.cadence.value,
        brief=when(answers),
        cap=setting.cap,
        ruin_bound=answers.risk.ruin_bound,
        kelly=answers.risk.kelly_backtest,
        collaborators=collaborators(answers),
        dated=setting.dated,
        answers=rows,
    )


def link_claude(root: Path) -> str:
    """`CLAUDE.md` as relative symlink to `AGENTS.md`; where symlinks fail,
    the one-line fallback. Returns which."""
    path = root / CLAUDE
    if path.is_symlink() or path.exists():
        path.unlink()
    try:
        os.symlink(AGENTS, path)
    except (OSError, NotImplementedError):
        write_atomic(path, FALLBACK)
        return "file"
    return "symlink"


def write_files(
    root: Path, read: Callable[[str], str], answers: Answers, setting: Setting
) -> str:
    """The three files; returns how `CLAUDE.md` landed."""
    write_atomic(root / README, readme(read("README.tmpl"), answers, setting))
    write_atomic(root / AGENTS, agents(read("AGENTS.tmpl"), answers, setting))
    return link_claude(root)


def refuse_existing(root: Path, *, force: bool) -> None:
    held = [
        name for name in FILES if (root / name).is_symlink() or (root / name).exists()
    ]
    if held and not force:
        raise CommandError(
            f"{root} already holds {', '.join(held)}; pass --force to rewrite them"
        )


def limit_values(answers: Answers, cap: int) -> dict[str, Any]:
    """Answers bound for `limits.json`, by dotted path."""
    return {
        "asset_cap": cap,
        "sizing.ruin_bound": answers.risk.ruin_bound,
        "sizing.kelly_fraction.backtest": answers.risk.kelly_backtest,
        "model_cutoff": None
        if answers.model_cutoff is None
        else answers.model_cutoff.isoformat(),
    }


def patched(document: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """`document` with each dotted path set; a fresh copy, input untouched."""
    out: dict[str, Any] = json.loads(json.dumps(document))
    for dotted, value in values.items():
        *parents, leaf = dotted.split(".")
        node = out
        for key in parents:
            node = node[key]
        node[leaf] = value
    return out


def limit_changes(answers: Answers, limits: Limits) -> dict[str, Any]:
    """What the operator must change in `limits.json` for these answers: each
    answered value differing from it. Absent cap or cutoff keeps the file's."""
    current = {
        "asset_cap": limits.asset_cap,
        "sizing.ruin_bound": limits.sizing.ruin_bound,
        "sizing.kelly_fraction.backtest": limits.sizing.kelly_fraction.backtest,
        "model_cutoff": None
        if limits.model_cutoff is None
        else limits.model_cutoff.isoformat(),
    }
    wanted = limit_values(answers, answers.capital.now or limits.asset_cap)
    if answers.model_cutoff is None:
        wanted["model_cutoff"] = current["model_cutoff"]
    return {key: value for key, value in wanted.items() if current[key] != value}


def preference_values(answers: Answers) -> dict[str, Any]:
    return {
        "focus_sectors": list(answers.universe.focus_sectors),
        "exclusions": answers.universe.exclusions.model_dump(mode="json"),
        "cadence": answers.horizon.cadence.value,
        "schedule": {
            "hour": answers.horizon.brief_hour,
            "days": answers.horizon.schedule.value,
        },
    }


def preference_batch(answers: Answers, held: Preferences) -> dict[str, Any]:
    """A `record` batch rewriting `preferences.json`; fields outside the
    answers survive."""
    return {
        "preferences": [
            {
                **held.model_dump(mode="json", exclude_none=True),
                **preference_values(answers),
            }
        ]
    }


def claude_ok(root: Path) -> bool:
    path = root / CLAUDE
    if path.is_symlink():
        return (
            os.readlink(path) == AGENTS or path.resolve() == (root / AGENTS).resolve()
        )
    return (
        path.is_file() and path.read_text(encoding="utf-8").strip() == FALLBACK.strip()
    )


def warnings(root: Path, template: str) -> list[dict[str, Any]]:
    """Absent `README.md` or `AGENTS.md`, `CLAUDE.md` neither link nor
    fallback, `AGENTS.md` invariants off template. Derived, never stored."""
    found: list[dict[str, Any]] = []
    for name in (README, AGENTS):
        if not (root / name).is_file():
            signal(f"no {name} in the book; run start --answers:file (load onboard)")
            found.append({"file": name, "problem": "absent"})
    if not claude_ok(root):
        signal(f"{CLAUDE} is neither a symlink to {AGENTS} nor {FALLBACK.strip()!r}")
        found.append({"file": CLAUDE, "problem": "not AGENTS.md link or fallback"})
    agents_path = root / AGENTS
    if agents_path.is_file() and section(
        agents_path.read_text(encoding="utf-8")
    ) != section(template):
        signal(f"{AGENTS} invariants section differs from template; restore it")
        found.append({"file": AGENTS, "problem": "invariants differ from template"})
    return found
