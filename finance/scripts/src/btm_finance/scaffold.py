"""What `start` writes: the book's layout, templates, and the held-out list
outside the book."""

from __future__ import annotations

import csv
import io
import json
import shlex
import shutil
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from importlib import resources
from pathlib import Path
from typing import Any

import btm_finance
from btm_corekit import (
    CommandError,
    ascii_words,
    make_id,
    now_iso,
    signal,
    write_atomic,
)
from btm_finance import onboarding
from btm_finance.models import (
    BASELINE_CONFIG,
    PREFERENCES_TEMPLATE,
    Answers,
    BookMeta,
    Status,
    limits_template,
)
from btm_finance.store import MARKER, held_out_path

DIRECTORIES = (
    "data/raw",
    "data/features",
    "ledger/pad",
    "ledger/runs",
    "proposals",
    "approvals",
    "rejected",
    "strategies/baseline",
    "features",
    "ext",
    "tests/reference",
    "lib",
    "tools",
    "research",
)
RESEARCH = {
    "backlog": "candidate hypotheses, one <id>.md each, ranked weekly",
    "calendar": "event calendars and trigger lists, one file per event family",
    "weekly": "weekly research note, one <YYYY-Www>.md each",
}
"""Queue folders under `research/`: name to purpose, one `INDEX.md` row
each."""
INDEX = "INDEX.md"
INDEX_HEAD = "# Index\n\npath | purpose | last touched\n"


def index_text(day: str) -> str:
    """Header, column line, one row per queue folder touched `day`."""
    rows = "".join(
        f"research/{name}/ | {purpose} | {day}\n" for name, purpose in RESEARCH.items()
    )
    return INDEX_HEAD + rows


def research_readme(name: str, purpose: str) -> str:
    return f"# {name}\n\nStatus: empty; {purpose}.\n"


BOOK_CONFTEST = """\"\"\"Book tests: book root first on sys.path, so
`import lib.<module>` resolves.

    uv run --project <skill scripts> pytest <book>/tests
\"\"\"

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
"""
UNONBOARDED = (
    "ask the operator the onboarding questions, write answers.json, run "
    "start with --answers:file; then load data, measure baseline, import "
    "holdings with record"
)
HELD_OUT_SHARE = 4  # one name in four per sector, rounded half up

BASELINE_README = """# baseline

Static comparator every candidate strategy is shown beside: equal weight on
the top third of names by average rank of 12-1 momentum, low volatility, and
book-to-market where filings are loaded; rebalanced annually. `start`
registers its hypothesis. `status` changes only on operator's word in chat,
recorded as decision hashing it.
"""


def template(name: str) -> str:
    return (resources.files(btm_finance) / "templates" / name).read_text(
        encoding="utf-8"
    )


def record_binding() -> tuple[str, ...]:
    """The skill's own binding, through the member's realpath, for the
    commands `README.md` and `AGENTS.md` show."""
    scripts = Path(btm_finance.__file__).resolve().parents[2]
    if not (scripts / "pyproject.toml").is_file():
        signal(f"no member manifest at {scripts}; fix the binding in AGENTS.md")
    return (
        "env",
        "-u",
        "VIRTUAL_ENV",
        "-u",
        "UV_PROJECT_ENVIRONMENT",
        "uv",
        "run",
        "--project",
        str(scripts),
        "btm-finance",
    )


def universe_rows(raw: str) -> list[tuple[str, str]]:
    """`symbol` and `sector` columns of a CSV, deduplicated, order kept."""
    reader = csv.DictReader(io.StringIO(raw))
    fields = {name.strip().lower(): name for name in reader.fieldnames or []}
    if "symbol" not in fields:
        raise CommandError("the universe CSV needs a symbol column (sector optional)")
    seen: dict[str, str] = {}
    for row in reader:
        symbol = (row.get(fields["symbol"]) or "").strip()
        sector = (row.get(fields["sector"]) or "").strip() if "sector" in fields else ""
        if symbol:
            seen.setdefault(symbol, sector or "unknown")
    return list(seen.items())


def stratified(rows: Sequence[tuple[str, str]]) -> dict[str, list[str]]:
    """Per sector, the first quarter by symbol, rounded half up. Deterministic:
    no randomness, no salt. O(n log n)."""
    sectors: dict[str, list[str]] = defaultdict(list)
    for symbol, sector in rows:
        sectors[sector].append(symbol)
    return {
        sector: sorted(names)[: (len(names) + HELD_OUT_SHARE // 2) // HELD_OUT_SHARE]
        for sector, names in sorted(sectors.items())
    }


def held_out(universe: str | None) -> dict[str, list[str]]:
    """The held-out list: sector to its held-out symbols, both sorted."""
    if universe is None:
        signal("no --universe:file; held-out list empty until start runs with one")
        return {}
    return stratified(universe_rows(universe))


def write_new(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, text)


def ignore(path: Path) -> None:
    """`data/` joined to `.gitignore`; other lines kept."""
    held = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = held.splitlines()
    if "data/" not in lines:
        write_atomic(path, "\n".join([*lines, "data/"]) + "\n")


def repository(root: Path) -> str:
    """`git init` unless `root` is inside a work tree; `absent` without git."""
    git = shutil.which("git")
    if git is None:
        signal("no git on PATH; book is not a repository: run git init in it")
        return "absent"
    inside = subprocess.run(
        [git, "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        check=False,
    )
    if inside.returncode == 0:
        return "inside"
    done = subprocess.run(
        [git, "-C", str(root), "init", "-q"], capture_output=True, check=False
    )
    if done.returncode != 0:
        signal(f"git init failed: {done.stderr.decode(errors='replace').strip()}")
        return "failed"
    return "init"


def outside(root: Path, path: Path) -> Path:
    """The held-out path, absolute; refused inside the book."""
    resolved = path.expanduser().resolve()
    if resolved.is_relative_to(root.resolve()):
        raise CommandError(
            f"--held-out {path} lies inside the book; name a path outside it"
        )
    return resolved


def onboard_files(
    root: Path, meta: BookMeta, answers: Answers, cap: int, dated: str
) -> str:
    """`README.md`, `AGENTS.md`, `CLAUDE.md` from the answers; returns how
    `CLAUDE.md` landed."""
    setting = onboarding.Setting(
        title=root.resolve().name,
        dated=dated[:10],
        cap=cap,
        held_out=meta.held_out or str(held_out_path(meta.id)),
        universe=(root / "universe.csv").is_file(),
        binding=shlex.join(record_binding()),
    )
    return onboarding.write_files(root, template, answers, setting)


def scaffold(
    root: Path,
    cap: int | None,
    universe: str | None,
    held_out_at: Path | None = None,
    answers: Answers | None = None,
) -> dict[str, Any]:
    """Make the book; refuse a directory that already holds `limits.json`.
    Flags win over answers; answers fill limits, preferences, and the three
    instruction files."""
    if (root / "limits.json").exists():
        raise CommandError(
            f"{root} already holds limits.json; start makes new books only"
        )
    book_id = make_id(ascii_words(root.resolve().name) or ["book"])
    answered = None if answers is None else answers.held_out
    default = held_out_path(book_id) if answered is None else Path(answered)
    hidden = outside(root, held_out_at or default)
    cap = cap or (answers.capital.now if answers else None) or onboarding.DEFAULT_CAP
    preferences = (
        PREFERENCES_TEMPLATE
        if answers is None
        else {**PREFERENCES_TEMPLATE, **onboarding.preference_values(answers)}
    )
    limits = (
        limits_template(cap)
        if answers is None
        else onboarding.patched(
            limits_template(cap), onboarding.limit_values(answers, cap)
        )
    )
    listing = held_out(universe)  # before any write: a bad CSV leaves nothing
    for directory in DIRECTORIES:
        (root / directory).mkdir(parents=True, exist_ok=True)
    write_new(hidden, json.dumps(listing, indent=2) + "\n")
    baseline = root / "strategies" / "baseline"
    write_new(baseline / "status", f"{Status.RESEARCH.value}\n")
    write_new(
        baseline / "config.json",
        json.dumps(BASELINE_CONFIG, indent=2) + "\n",
    )
    write_new(baseline / "README.md", BASELINE_README)
    write_new(baseline / "signal.py", template("signal.tmpl"))
    if universe is not None:
        write_new(root / "universe.csv", universe)
    write_new(root / "lib" / "__init__.py", "")
    write_new(root / "tests" / "conftest.py", BOOK_CONFTEST)
    for name, purpose in RESEARCH.items():
        write_new(
            root / "research" / name / "README.md", research_readme(name, purpose)
        )
    write_new(root / INDEX, index_text(now_iso()[:10]))
    write_new(root / "preferences.json", json.dumps(preferences, indent=2) + "\n")
    write_new(root / "limits.json", json.dumps(limits, indent=2) + "\n")
    meta = BookMeta(
        id=book_id,
        created=now_iso(),
        engine=btm_finance.__version__,
        held_out=str(hidden),
    )
    write_new(root / MARKER, json.dumps(meta.model_dump(mode="json"), indent=2) + "\n")
    claude = (
        None
        if answers is None
        else onboard_files(root, meta, answers, cap, meta.created)
    )
    ignore(root / ".gitignore")
    git = repository(root)
    return {
        "book": book_id,
        "path": str(root.resolve()),
        "held_out": {
            "path": str(hidden),
            "names": sum(len(names) for names in listing.values()),
        },
        "wrote": [
            "limits.json",
            "preferences.json",
            ".gitignore",
            MARKER,
            INDEX,
            "lib/__init__.py",
            "tests/conftest.py",
            *(f"research/{name}/README.md" for name in RESEARCH),
            "strategies/baseline/",
            *(["universe.csv"] if universe is not None else []),
            *(onboarding.FILES if claude is not None else ()),
        ],
        "onboarded": claude is not None,
        **({} if claude is None else {"claude_md": claude}),
        "git": git,
        "next": UNONBOARDED
        if claude is None
        else "load data, then measure baseline; import holdings with record",
    }
