"""Onboarding: `start --answers` and `onboard` write `README.md`, `AGENTS.md`,
`CLAUDE.md`; answers fill limits and preferences; bare `check` warns on each
file absent or drifted."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from btm_finance import onboarding
from btm_finance.models import ANSWERS_SHAPE, Answers
from btm_finance.scaffold import template

ANSWERS = {
    "jurisdiction": "CA",
    "broker": {
        "name": "Northbank",
        "accounts": [{"name": "tfsa", "kind": "sheltered"}],
        "sleeve_account": "tfsa",
    },
    "capital": {"now": 50000, "six_months": 80000},
    "risk": {"ruin_bound": 0.3, "kelly_backtest": 0.2},
    "horizon": {"cadence": "quarterly"},
    "universe": {
        "focus_sectors": ["Energy"],
        "exclusions": {"symbols": [], "sectors": ["Tobacco"], "countries": []},
    },
    "model_cutoff": "2025-06-30",
    "collaborators": [{"name": "codex", "kind": "agent", "may_propose": True}],
}


def started(run, root: Path, answers: dict | None, *extra: str):
    argv = ["start", str(root), *extra]
    if answers is None:
        return run(argv)
    return run([*argv, "--answers:stdin"], stdin=json.dumps(answers))


def problems(run, book: Path) -> list[dict]:
    view = run(["check", str(book)])[1]
    return [w for w in view["warnings"] if w.get("file") in onboarding.FILES]


def test_start_with_answers_writes_the_three_files_and_fills_limits(tmp_path, run):
    root = tmp_path / "book"
    code, receipt, err = started(run, root, ANSWERS)
    assert code == 0, err
    assert receipt["onboarded"] is True
    assert receipt["claude_md"] == "symlink"
    assert {"README.md", "AGENTS.md", "CLAUDE.md"} <= set(receipt["wrote"])
    assert os.readlink(root / "CLAUDE.md") == "AGENTS.md"
    limits = json.loads((root / "limits.json").read_text())
    assert limits["asset_cap"] == 50000
    assert limits["sizing"]["ruin_bound"] == 0.3
    assert limits["sizing"]["kelly_fraction"] == {
        "backtest": 0.2,
        "paper": 0.5,
        "live": 0.75,
    }
    assert limits["model_cutoff"] == "2025-06-30"
    assert json.loads((root / "preferences.json").read_text()) == {
        "focus_sectors": ["Energy"],
        "exclusions": {"symbols": [], "sectors": ["Tobacco"], "countries": []},
        "cadence": "quarterly",
    }
    readme = (root / "README.md").read_text()
    created = json.loads((root / "book.json").read_text())["created"][:10]
    assert f"as of {created}" in readme
    assert "| 3. Capital | now 50000; in six months 80000 |" in readme
    assert "Northbank" in readme and "account tfsa" in readme
    agents = (root / "AGENTS.md").read_text()
    assert "codex (agent) may propose" in agents
    assert "rebalance quarterly" in agents
    assert "$" not in agents
    assert problems(run, root) == []


def test_flags_win_over_answers(tmp_path, run):
    hidden = tmp_path / "elsewhere" / "held.json"
    answers = {**ANSWERS, "held_out": str(tmp_path / "answered.json")}
    code, receipt, err = started(
        run, tmp_path / "book", answers, "--cap", "70000", "--held-out", str(hidden)
    )
    assert code == 0, err
    assert receipt["held_out"]["path"] == str(hidden.resolve())
    limits = json.loads((tmp_path / "book" / "limits.json").read_text())
    assert limits["asset_cap"] == 70000


def test_answers_held_out_path_is_used_when_no_flag(tmp_path, run):
    path = tmp_path / "answered.json"
    code, receipt, _ = started(run, tmp_path / "book", {"held_out": str(path)})
    assert code == 0
    assert receipt["held_out"]["path"] == str(path.resolve())
    assert str(path.resolve()) in (tmp_path / "book" / "README.md").read_text()


def test_start_without_answers_writes_none_of_the_three(tmp_path, run):
    root = tmp_path / "book"
    code, receipt, _ = started(run, root, None)
    assert code == 0
    assert receipt["onboarded"] is False
    assert "claude_md" not in receipt
    assert "onboard" in receipt["next"]
    for name in onboarding.FILES:
        assert not (root / name).exists() and not (root / name).is_symlink()
    assert json.loads((root / "limits.json").read_text())["asset_cap"] == 10_000_000


def test_partial_answers_take_defaults():
    answers = Answers.model_validate({"capital": {"now": 1000}})
    setting = onboarding.Setting(
        title="b",
        dated="2026-01-02",
        cap=1000,
        held_out="/x/held.json",
        universe=False,
        binding="btm-finance",
    )
    readme = onboarding.readme(template("README.tmpl"), answers, setting)
    assert "as of 2026-01-02" in readme
    assert "| 3. Capital | now 1000; in six months not given (default) |" in readme
    assert "ruin_bound 0.35 (default); Kelly backtest 0.25 (default)" in readme
    assert "rebalance monthly (default)" in readme
    assert "csv, edgar, french (default)" in readme
    assert "| 10. Collaborators | operator only (default) |" in readme
    assert "| 9. Held-out path | /x/held.json (default) |" in readme
    assert "no API in use" in readme
    agents = onboarding.agents(template("AGENTS.tmpl"), answers, setting)
    assert "Operator alone works here" in agents
    assert onboarding.section(agents) == onboarding.section(template("AGENTS.tmpl"))


def test_invariants_section_holds_no_placeholder():
    section = onboarding.section(template("AGENTS.tmpl"))
    assert section is not None and "$" not in section
    assert "No agent, script, or cron changes these four." in section


def test_answers_refuse_unknown_keys_such_as_a_secret(tmp_path, run):
    bad = {"sources": {"tiingo_api_key": "abc"}}
    code, _, err = started(run, tmp_path / "book", bad)
    assert code == 1
    assert "tiingo_api_key" in err
    assert not (tmp_path / "book").exists()


def test_sleeve_account_must_name_an_account():
    with pytest.raises(ValueError, match="names none of accounts"):
        Answers.model_validate(
            {
                "broker": {
                    "accounts": [{"name": "a", "kind": "taxable"}],
                    "sleeve_account": "b",
                }
            }
        )


def test_onboard_writes_files_on_an_existing_book(tmp_path, run):
    root = tmp_path / "book"
    started(run, root, None)
    limits_before = (root / "limits.json").read_bytes()
    preferences_before = (root / "preferences.json").read_bytes()
    ledger_before = (root / "ledger" / "hypotheses.jsonl").read_bytes()
    assert {w["file"] for w in problems(run, root)} == set(onboarding.FILES)
    code, receipt, err = run(
        ["onboard", str(root), "--answers:stdin"], stdin=json.dumps(ANSWERS)
    )
    assert code == 0, err
    assert receipt["claude_md"] == "symlink"
    assert receipt["limits"] == {
        "asset_cap": 50000,
        "sizing.ruin_bound": 0.3,
        "sizing.kelly_fraction.backtest": 0.2,
        "model_cutoff": "2025-06-30",
    }
    assert receipt["preferences"] == {
        "preferences": [
            {
                "focus_sectors": ["Energy"],
                "exclusions": {"symbols": [], "sectors": ["Tobacco"], "countries": []},
                "cadence": "quarterly",
            }
        ]
    }
    assert (root / "limits.json").read_bytes() == limits_before
    assert (root / "preferences.json").read_bytes() == preferences_before
    assert (root / "ledger" / "hypotheses.jsonl").read_bytes() == ledger_before
    today = datetime.now(UTC).date().isoformat()
    assert f"as of {today}" in (root / "README.md").read_text()
    assert problems(run, root) == []
    code, _, err = run(
        ["record", str(root), "--batch:stdin"], stdin=json.dumps(receipt["preferences"])
    )
    assert code == 0, err


def test_onboard_returns_only_limits_that_differ(tmp_path, run):
    root = tmp_path / "book"
    started(run, root, None)
    code, receipt, _ = run(["onboard", str(root), "--answers:stdin"], stdin="{}")
    assert code == 0
    assert receipt["limits"] == {}


def test_onboard_refuses_existing_files_without_force(book, run):
    agents = (book / "AGENTS.md").read_bytes()
    code, _, err = run(
        ["onboard", str(book), "--answers:stdin"], stdin=json.dumps(ANSWERS)
    )
    assert code == 1
    assert "--force" in err and "AGENTS.md" in err
    assert (book / "AGENTS.md").read_bytes() == agents
    code, _, err = run(
        ["onboard", str(book), "--force", "--answers:stdin"],
        stdin=json.dumps(ANSWERS),
    )
    assert code == 0, err
    assert "codex (agent) may propose" in (book / "AGENTS.md").read_text()


def test_fallback_claude_md_when_symlinks_fail(tmp_path, run, monkeypatch):
    def refuse(*_args, **_kwargs):
        raise OSError("symlinks unsupported")

    monkeypatch.setattr(onboarding.os, "symlink", refuse)
    root = tmp_path / "book"
    code, receipt, _ = started(run, root, {})
    assert code == 0
    assert receipt["claude_md"] == "file"
    assert not (root / "CLAUDE.md").is_symlink()
    assert (root / "CLAUDE.md").read_text() == "Read AGENTS.md.\n"
    assert problems(run, root) == []


def test_each_warning_fires_and_clears(book, run):
    assert problems(run, book) == []
    readme = (book / "README.md").read_text()
    (book / "README.md").unlink()
    assert problems(run, book) == [{"file": "README.md", "problem": "absent"}]
    (book / "README.md").write_text(readme)

    (book / "CLAUDE.md").unlink()
    (book / "CLAUDE.md").write_text("see agents\n")
    claude = [{"file": "CLAUDE.md", "problem": "not AGENTS.md link or fallback"}]
    assert problems(run, book) == claude
    (book / "CLAUDE.md").unlink()
    (book / "CLAUDE.md").symlink_to("README.md")
    assert problems(run, book) == claude
    (book / "CLAUDE.md").unlink()
    (book / "CLAUDE.md").symlink_to("AGENTS.md")
    assert problems(run, book) == []

    agents = (book / "AGENTS.md").read_text()
    (book / "AGENTS.md").write_text(agents.replace("these four", "these three"))
    err = run(["check", str(book)])[2]
    assert problems(run, book) == [
        {"file": "AGENTS.md", "problem": "invariants differ from template"}
    ]
    assert "invariants section differs" in err
    (book / "AGENTS.md").write_text(agents.replace("## Book", "## Book\n\n- Extra."))
    assert problems(run, book) == []

    (book / "AGENTS.md").unlink()
    assert problems(run, book) == [{"file": "AGENTS.md", "problem": "absent"}]


def test_schema_prints_answers_whose_shape_decodes(run):
    code, document, _ = run(["schema"])
    assert code == 0
    assert document["answers"] == ANSWERS_SHAPE
    assert "keys live in the environment" in document["answers_rules"]
    Answers.model_validate(document["answers"])
