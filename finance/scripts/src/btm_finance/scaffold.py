"""What `start` writes: the book's layout, templates, deny rules, sender, and
the held-out list outside the book."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
from collections import defaultdict
from collections.abc import Iterable, Sequence
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
from btm_finance.models import PREFERENCES_TEMPLATE, BookMeta, Status, limits_template
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
    ".claude",
)
SENTINEL = "RECORD: tuple[str, ...] = ()"
HELD_OUT_SHARE = 4  # one name in four per sector, rounded half up

BASELINE_README = """# baseline

Static comparator every candidate strategy is shown beside. `signal.py` is a
placeholder (equal weight); replace it with the static multi-factor baseline
before scoring. The human alone edits `status`.
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


def deny_rules(root: Path, held_out: Path) -> list[str]:
    """Claude Code deny entries for the four invariants; `//` is absolute."""
    book = root.resolve().as_posix()
    hidden = held_out.parent.resolve().as_posix()
    return [
        "Bash(*bin/send*)",
        f"Read(/{hidden}/**)",
        f"Edit(/{book}/ledger/**)",
        f"Write(/{book}/ledger/**)",
        f"Edit(/{book}/approvals/**)",
        f"Write(/{book}/approvals/**)",
    ]


def settings(path: Path, rules: Iterable[str]) -> str:
    """Existing settings kept; the deny rules joined into `permissions.deny`."""
    held: dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as err:
            raise CommandError(f"unreadable {path}: {err}") from err
        held = loaded if isinstance(loaded, dict) else {}
    permissions = held.setdefault("permissions", {})
    deny = list(permissions.get("deny", []))
    permissions["deny"] = deny + [rule for rule in rules if rule not in deny]
    return json.dumps(held, indent=2) + "\n"


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


def member(salt: str, symbol: str) -> str:
    return hashlib.sha256(f"{salt}:{symbol}".encode()).hexdigest()


def stratified(rows: Sequence[tuple[str, str]], salt: str) -> dict[str, list[str]]:
    """Per sector, the quarter whose salted digests sort first. O(n log n)."""
    sectors: dict[str, list[str]] = defaultdict(list)
    for symbol, sector in rows:
        sectors[sector].append(symbol)
    return {
        sector: sorted(names, key=lambda symbol: member(salt, symbol))[
            : (len(names) + HELD_OUT_SHARE // 2) // HELD_OUT_SHARE
        ]
        for sector, names in sorted(sectors.items())
    }


def held_out(book_id: str, universe: str | None) -> dict[str, Any]:
    """The salted membership list: digests only, so the file names no symbol."""
    salt = secrets.token_hex(16)
    rows = universe_rows(universe) if universe is not None else []
    chosen = stratified(rows, salt)
    if universe is None:
        signal("no --universe:file; held-out list empty until start runs with one")
    return {
        "book": book_id,
        "salt": salt,
        "members": sorted(member(salt, s) for names in chosen.values() for s in names),
        "universe": len(rows),
        "by_sector": {
            sector: {
                "held_out": len(names),
                "universe": sum(1 for _, s in rows if s == sector),
            }
            for sector, names in chosen.items()
        },
    }


def write_new(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, text)


def scaffold(root: Path, cap: int, universe: str | None) -> dict[str, Any]:
    """Make the book; refuse a directory that already holds `limits.json`."""
    if (root / "limits.json").exists():
        raise CommandError(
            f"{root} already holds limits.json; start makes new books only"
        )
    book_id = make_id(ascii_words(root.resolve().name) or ["book"])
    hidden = held_out_path(book_id)
    listing = held_out(book_id, universe)  # before any write: a bad CSV leaves nothing
    for directory in DIRECTORIES:
        (root / directory).mkdir(parents=True, exist_ok=True)
    write_new(hidden, json.dumps(listing, indent=2) + "\n")
    baseline = root / "strategies" / "baseline"
    write_new(baseline / "status", f"{Status.RESEARCH.value}\n")
    write_new(
        baseline / "config.json",
        json.dumps({"name": "baseline", "comparator": True}, indent=2) + "\n",
    )
    write_new(baseline / "README.md", BASELINE_README)
    write_new(baseline / "signal.py", template("signal.tmpl"))
    claude = root / ".claude" / "settings.json"
    write_new(claude, settings(claude, deny_rules(root, hidden)))
    send = root / "bin" / "send"
    write_new(send, sender(record_binding()))
    send.chmod(0o755)
    write_new(
        root / "preferences.json", json.dumps(PREFERENCES_TEMPLATE, indent=2) + "\n"
    )
    write_new(root / "limits.json", json.dumps(limits_template(cap), indent=2) + "\n")
    meta = BookMeta(id=book_id, created=now_iso(), engine=btm_finance.__version__)
    write_new(root / MARKER, json.dumps(meta.model_dump(mode="json"), indent=2) + "\n")
    return {
        "book": book_id,
        "path": str(root.resolve()),
        "held_out": {"path": str(hidden), "names": len(listing["members"])},
        "wrote": [
            "limits.json",
            "preferences.json",
            MARKER,
            "bin/send",
            ".claude/settings.json",
            "strategies/baseline/",
        ],
        "next": "import holdings and preferences with record, then register "
        "the baseline hypothesis",
    }
