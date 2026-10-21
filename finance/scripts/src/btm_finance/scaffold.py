"""What `start` writes: the book's layout, templates, sender, and the
held-out list outside the book."""

from __future__ import annotations

import csv
import io
import json
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
from btm_finance.models import (
    BASELINE_CONFIG,
    PREFERENCES_TEMPLATE,
    BookMeta,
    Status,
    limits_template,
)
from btm_finance.store import MARKER, held_out_path

DIRECTORIES = (
    "bin",
    "data/raw",
    "data/features",
    "ledger/pad",
    "ledger/runs",
    "proposals",
    "approvals",
    "rejected",
    "sent",
    "strategies/baseline",
    "features",
    "ext",
    "tests/reference",
    "lib",
    "tools",
    "research",
)
INDEX = "INDEX.md"
INDEX_TEXT = "# Index\n\npath | purpose | last touched\n"
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
SENTINEL = "RECORD: tuple[str, ...] = ()"
HELD_OUT_SHARE = 4  # one name in four per sector, rounded half up

BASELINE_README = """# baseline

Static comparator every candidate strategy is shown beside: equal weight on
the top third of names by average rank of 12-1 momentum, low volatility, and
book-to-market where filings are loaded; rebalanced annually. `start`
registers its hypothesis. The human alone edits `status`.
"""


def template(name: str) -> str:
    return (resources.files(btm_finance) / "templates" / name).read_text(
        encoding="utf-8"
    )


def record_binding() -> tuple[str, ...]:
    """The skill's own binding, through the member's realpath."""
    scripts = Path(btm_finance.__file__).resolve().parents[2]
    if not (scripts / "pyproject.toml").is_file():
        signal(f"no member manifest at {scripts}; edit RECORD in bin/send")
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


def sender(binding: Sequence[str]) -> str:
    text = template("send.py")
    if text.count(SENTINEL) != 1:
        raise CommandError("send template lost its RECORD line; reinstall the skill")
    return text.replace(SENTINEL, f"RECORD: tuple[str, ...] = {tuple(binding)!r}")


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


def scaffold(
    root: Path, cap: int, universe: str | None, held_out_at: Path | None = None
) -> dict[str, Any]:
    """Make the book; refuse a directory that already holds `limits.json`."""
    if (root / "limits.json").exists():
        raise CommandError(
            f"{root} already holds limits.json; start makes new books only"
        )
    book_id = make_id(ascii_words(root.resolve().name) or ["book"])
    hidden = outside(root, held_out_at or held_out_path(book_id))
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
    write_new(root / INDEX, INDEX_TEXT)
    send = root / "bin" / "send"
    write_new(send, sender(record_binding()))
    send.chmod(0o755)
    write_new(
        root / "preferences.json", json.dumps(PREFERENCES_TEMPLATE, indent=2) + "\n"
    )
    write_new(root / "limits.json", json.dumps(limits_template(cap), indent=2) + "\n")
    meta = BookMeta(
        id=book_id,
        created=now_iso(),
        engine=btm_finance.__version__,
        held_out=str(hidden),
    )
    write_new(root / MARKER, json.dumps(meta.model_dump(mode="json"), indent=2) + "\n")
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
            "bin/send",
            INDEX,
            "lib/__init__.py",
            "tests/conftest.py",
            "strategies/baseline/",
            *(["universe.csv"] if universe is not None else []),
        ],
        "git": git,
        "next": "load data, then measure baseline; import holdings and "
        "preferences with record",
    }
