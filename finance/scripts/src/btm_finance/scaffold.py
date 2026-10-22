"""What `start` writes: the book's layout, templates, and the held-out list
outside the book. The one git call in the package lives here: `git init`
when the book lies in no repository; nothing is ever committed."""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from importlib import resources
from pathlib import Path
from string import Template
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
from btm_finance.delegation import FOLDER, SEEDED, seed
from btm_finance.ledger import Kind
from btm_finance.models import (
    BASELINE_CONFIG,
    PREFERENCES_TEMPLATE,
    BookMeta,
    Status,
    limits_template,
)
from btm_finance.store import MARKER, PAD_DIR, held_out_path

DEFAULT_CAP = 10_000_000
DIRECTORIES = (
    "data/raw",
    "data/features",
    PAD_DIR.as_posix(),
    "ledger/runs",
    "proposals",
    "strategies/baseline",
    "lib",
    "tools",
    "research",
    "tests",
    FOLDER,
)
LEDGER = (Kind.CRITIQUE, Kind.DECISION, Kind.FILL, Kind.RUN)
"""Ledger files `start` makes empty; `record` writes the hypotheses file."""
INDEX = "INDEX.md"
INDEX_HEAD = "# Index\n\npath | purpose\n"
AGENTS = "AGENTS.md"
CLAUDE = "CLAUDE.md"
FALLBACK = "Read AGENTS.md.\n"
IGNORED = ("/data", "__pycache__/")


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
HELD_OUT_SHARE = 4  # one name in four per sector, rounded half up

BASELINE_README = """# baseline

Static comparator every candidate strategy is shown beside: equal weight on
the top third of names by average rank of 12-1 momentum, low volatility, and
book-to-market where filings are loaded; rebalanced annually. `start`
registers its hypothesis. `status` changes only on operator's word.
"""


def template(name: str) -> str:
    return (resources.files(btm_finance) / "templates" / name).read_text(
        encoding="utf-8"
    )


def scripts_root() -> Path:
    """The skill's `scripts` project, realpath: `src/btm_finance/` two levels
    under it; `AGENTS.md` binds `uv run --project` to it."""
    return Path(btm_finance.__file__).resolve().parents[2]


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
    """`/data` and `__pycache__/` joined to `.gitignore`; other lines kept."""
    held = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = held.splitlines()
    missing = [line for line in IGNORED if line not in lines]
    if missing:
        write_atomic(path, "\n".join([*lines, *missing]) + "\n")


def outside(root: Path, path: Path) -> Path:
    """The held-out path, absolute; refused inside the book."""
    resolved = path.expanduser().resolve()
    if resolved.is_relative_to(root.resolve()):
        raise CommandError(
            f"--held-out {path} lies inside the book; name a path outside it"
        )
    return resolved


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


def repository(root: Path) -> str:
    """`inside` when `root` lies in a work tree, else `init` after `git init
    -q -b main`; `absent` with a signal when git is not on PATH."""
    found = shutil.which("git")
    if found is None:
        signal("no git on PATH; the book is no repository until git init runs")
        return "absent"
    probe = [found, "-C", str(root), "rev-parse", "--is-inside-work-tree"]
    if subprocess.run(probe, capture_output=True, check=False).returncode == 0:
        return "inside"
    done = subprocess.run(
        [found, "-C", str(root), "init", "-q", "-b", "main"],
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        raise CommandError(f"git init in {root} failed: {done.stderr.decode().strip()}")
    return "init"


def scaffold(
    root: Path, cap: int | None, universe: str | None, held_out_at: Path | None = None
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
    for kind in LEDGER:
        (root / "ledger" / kind.file).touch()
    write_new(hidden, json.dumps(listing, indent=2) + "\n")
    baseline = root / "strategies" / "baseline"
    write_new(baseline / "status", f"{Status.RESEARCH.value}\n")
    write_new(baseline / "config.json", json.dumps(BASELINE_CONFIG, indent=2) + "\n")
    write_new(baseline / "README.md", BASELINE_README)
    write_new(baseline / "signal.py", template("signal.tmpl"))
    if universe is not None:
        write_new(root / "universe.csv", universe)
    write_new(root / "lib" / "__init__.py", "")
    for unit in SEEDED:
        write_new(root / FOLDER / f"{unit}.md", seed(unit))
    write_new(root / "tests" / "conftest.py", BOOK_CONFTEST)
    write_new(root / INDEX, INDEX_HEAD)
    write_new(
        root / "preferences.json", json.dumps(PREFERENCES_TEMPLATE, indent=2) + "\n"
    )
    limits = limits_template(cap or DEFAULT_CAP)
    write_new(root / "limits.json", json.dumps(limits, indent=2) + "\n")
    write_new(
        root / AGENTS,
        Template(template("AGENTS.tmpl")).safe_substitute(
            title=root.resolve().name, scripts=scripts_root(), book=root.resolve()
        ),
    )
    claude = link_claude(root)
    meta = BookMeta(
        id=book_id,
        created=now_iso(),
        engine=btm_finance.__version__,
        held_out=str(hidden),
    )
    write_new(root / MARKER, json.dumps(meta.model_dump(mode="json"), indent=2) + "\n")
    ignore(root / ".gitignore")
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
            AGENTS,
            CLAUDE,
            "lib/__init__.py",
            "tests/conftest.py",
            "strategies/baseline/",
            *(f"{FOLDER}/{unit}.md" for unit in SEEDED),
            *(f"ledger/{kind.file}" for kind in LEDGER),
            *(["universe.csv"] if universe is not None else []),
        ],
        "claude_md": claude,
        "git": repository(root),
        "next": "load data, then measure baseline; import holdings as opening fills",
    }
