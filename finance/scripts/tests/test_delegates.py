"""The dispatcher: a receipt decodes or names every problem, the miner's
training folds hold no test-block date and no held-out name, and a lead
running two disjoint delegates in parallel records each receipt only after
examining it, with bare `check` warning on a `wrote` path that vanished."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from btm_finance import api
from btm_finance.models import DelegateKind, Receipt

from btm_corekit import CommandError

PAD = ("ledger", "pad", "scratch.jsonl")
ABSENT = "receipt path absent"

EXAMPLE: dict[str, object] = {
    "unit": "author",
    "status": "done",
    "wrote": ["strategies/value-tilt/signal.py", "ledger/runs/author-1.jsonl"],
    "pad": [],
    "ids": {"run_id": "value-tilt-abc", "hypothesis": "value-tilt-def"},
    "summary": "Measured value tilt once; scorecard written; DSR 0.71 blocks.",
    "next": "critique run value-tilt-abc",
    "friction": "",
}


def test_receipt_accepts_the_contract_example():
    found = api.receipt(json.dumps(EXAMPLE))
    assert found.unit is DelegateKind.AUTHOR
    assert found.ids["run_id"] == "value-tilt-abc"


def test_receipt_names_every_problem_at_once():
    bad = EXAMPLE | {
        "unit": "oracle",
        "summary": " ".join(["word"] * 41),
        "wrote": ["../outside.md", "/etc/passwd"],
    }
    with pytest.raises(CommandError) as caught:
        api.receipt(json.dumps(bad))
    message = str(caught.value)
    for fragment in ("unit", "41 words", "'../outside.md'", "'/etc/passwd'"):
        assert fragment in message, fragment


def test_receipt_refuses_extra_keys_prose_and_two_line_next():
    for text in (
        json.dumps(EXAMPLE | {"notes": "long working notes"}),
        json.dumps(EXAMPLE | {"next": "one\ntwo"}),
        "Done! Here is what I found.",
        "[]",
    ):
        with pytest.raises(CommandError):
            api.receipt(text)


def test_schema_prints_the_receipt_shape(run):
    code, schema, _ = run(["check", "--schema", "receipt"])
    assert code == 0
    assert list(schema["receipt"]["receipt"]) == list(Receipt.model_fields)


def test_agents_md_holds_one_short_brief_per_kind(book):
    text = (book / "AGENTS.md").read_text()
    section = text.split("## Delegates", 1)[1].split("\n## ", 1)[0]
    briefs = section.split("\n- ")[1:]
    assert [brief.split(".", 1)[0] for brief in briefs] == list(DelegateKind)
    for brief in briefs:
        assert len(brief.split()) < 150
        assert " ".join(brief.split()).endswith(
            "Your final message is the receipt and nothing else."
        )
    assert "uv run --project" in section and "python -c" in section


def held_names(book: Path) -> set[str]:
    hidden = json.loads((book / "book.json").read_text())["held_out"]
    listing = json.loads(Path(hidden).read_text())
    return {name for names in listing.values() for name in names}


def test_training_folds_hide_the_test_block_and_held_out_names(synthetic):
    book = synthetic(seed=7)
    found = api.research(api.open_book(str(book)))
    every = found.dates
    folds = json.loads((book / "limits.json").read_text())["thresholds"]["folds"]
    start = int(np.array_split(np.arange(len(every)), folds)[-1][0])
    training = found.folds("train")
    assert training.dates == every[:start]
    market = training.at(every[start - 1])
    closes = market.close(len(every))
    assert np.isnan(closes[: len(every) - start]).all()
    assert np.isfinite(closes[-1]).all()
    assert held_names(book) and not held_names(book) & set(market.names)
    for later in (every[start], every[-1], date(2100, 1, 1)):
        with pytest.raises(CommandError, match="outside training dates"):
            training.at(later)
    with pytest.raises(CommandError, match="miner rule"):
        found.folds("test")


def delegate(book: Path, kind: str, path: str) -> str:
    """A simulated delegate: writes inside its own scope, returns a receipt."""
    target = book / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# {kind} note\n", encoding="utf-8")
    return json.dumps(
        EXAMPLE
        | {
            "unit": kind,
            "wrote": [path],
            "ids": {},
            "summary": f"{kind} wrote one note.",
            "next": "",
        }
    )


def examined(book: Path, text: str) -> Receipt:
    """The lead's examine: shape first, then every `wrote` path exists."""
    found = api.receipt(text)
    assert all((book / path).is_file() for path in found.wrote)
    return found


def absent(view: dict) -> list[dict]:
    return [w for w in view["warnings"] if w.get("problem") == ABSENT]


def test_lead_dispatches_two_disjoint_delegates_and_records_receipts(book, run):
    units = [
        ("reader", "research/abc/2026-10-01-10-q.md"),
        ("librarian", "research/literature/momentum.md"),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        texts = list(pool.map(lambda unit: delegate(book, *unit), units))
    accepted = [examined(book, text) for text in texts]
    assert {r.unit for r in accepted} == {DelegateKind.READER, DelegateKind.LIBRARIAN}
    now = datetime.now(UTC)
    with book.joinpath(*PAD).open("a", encoding="utf-8") as pad:
        for offset, found in enumerate(accepted):
            line = found.model_dump(mode="json") | {
                "ts": (now + timedelta(seconds=offset)).isoformat(),
                "type": "receipt",
            }
            pad.write(json.dumps(line) + "\n")
    code, view, err = run(["check", str(book)])
    assert code == 0, err
    assert absent(view) == []
    (book / units[1][1]).unlink()
    code, view, err = run(["check", str(book)])
    assert code == 0
    assert absent(view) == [
        {
            "problem": ABSENT,
            "unit": "librarian",
            "ts": (now + timedelta(seconds=1)).isoformat(),
            "path": units[1][1],
        }
    ]
    assert "receipt path(s) absent" in err
