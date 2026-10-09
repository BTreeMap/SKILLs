"""The command surface end to end, against an isolated state root."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from btm_draft_paper.cli import main


@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
    return tmp_path


@pytest.fixture
def artifacts(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    (root / "runs").mkdir(parents=True)
    (root / "runs" / "metrics.json").write_text("{}", encoding="utf-8")
    return root


def run(
    argv: list[str], capsys: pytest.CaptureFixture[str], stdin: str | None = None
) -> tuple[int, Any, str]:
    original = sys.stdin
    if stdin is not None:
        sys.stdin = io.StringIO(stdin)
    try:
        code = main(argv)
    finally:
        sys.stdin = original
    captured = capsys.readouterr()
    document = json.loads(captured.out) if captured.out.strip() else None
    return code, document, captured.err


def opened(
    capsys: pytest.CaptureFixture[str],
    artifacts: Path,
    verb: str = "build",
    status: str = "partial",
) -> str:
    code, document, err = run(
        [
            "start",
            "tail latency",
            "--verb",
            verb,
            "--format",
            "full",
            "--status",
            status,
            "--venue",
            "NSDI 2027",
            "--model",
            "model-v1",
            "--artifacts",
            str(artifacts),
        ],
        capsys,
    )
    assert code == 0, err
    return str(document["session"])


def record(
    session: str, capsys: pytest.CaptureFixture[str], *events: dict[str, Any]
) -> tuple[int, Any, str]:
    return run(["record", session], capsys, stdin=json.dumps({"events": list(events)}))


def trace_of(session: str, root: Path) -> list[dict[str, Any]]:
    path = root / "state/btm-skills/draft-paper/sessions" / session / "trace.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


SUPPORTED = {
    "event": "claim-added",
    "kw": ["p99", "drop"],
    "text": "p99 latency drops 30%",
    "status": "supported",
    "artifact": "runs/metrics.json",
    "location": "summary.p99",
}
PLANNED = {
    "event": "claim-added",
    "kw": ["scale", "out"],
    "text": "throughput scales to 64 nodes",
    "status": "to-run",
    "artifact": "runs/scale.json",
}


def stage(n: int) -> dict[str, Any]:
    return {"event": "stage-started", "stage": n}


def request(gate: str) -> dict[str, Any]:
    return {"event": "gate-requested", "gate": gate}


def decide(gate: str, outcome: str) -> dict[str, Any]:
    return {"event": "gate-decided", "gate": gate, "outcome": outcome, "reply": "ok"}


class TestInit:
    def test_a_verb_and_input_status_that_do_not_fit_are_refused(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        code, _, err = run(
            [
                *("start", "a b", "--verb", "design", "--format", "short"),
                *("--status", "full", "--venue", "v", "--model", "m"),
                *("--artifacts", str(artifacts)),
            ],
            capsys,
        )
        assert code == 1
        assert "a design run starts from initial or shaped" in err

    def test_a_fresh_run_points_at_its_first_stage(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts, status="shaped")
        code, document, _ = run(["status", session], capsys)
        assert code == 0
        assert document["stages"] == [1, 8]
        assert document["gates"] == {"plan": "open", "ledger": "open", "draft": "open"}
        assert document["next"] == "record stage-started 1"


class TestNote:
    def test_the_script_stamps_time_and_run_and_numbers_nothing(
        self,
        capsys: pytest.CaptureFixture[str],
        artifacts: Path,
        isolated_state: Path,
    ) -> None:
        session = opened(capsys, artifacts)
        code, document, _ = record(session, capsys, stage(2), SUPPORTED)
        assert code == 0
        made = document["new"]["p99-drop"]
        rows = trace_of(session, isolated_state)
        assert [set(row) for row in rows] == [
            {"t", "run", "event", "stage"},
            {"t", "run", "event", "id", "text", "status", "artifact", "location"},
        ]
        assert {row["run"] for row in rows} == {session}
        assert rows[1]["id"] == made

    def test_a_rejected_batch_names_every_problem_and_appends_nothing(
        self,
        capsys: pytest.CaptureFixture[str],
        artifacts: Path,
        isolated_state: Path,
    ) -> None:
        session = opened(capsys, artifacts)
        code, document, _ = record(
            session,
            capsys,
            stage(2),
            {"event": "nap"},
            {**stage(3), "seq": 2},
            request("draft"),
        )
        assert code == 1
        wheres = [problem["where"] for problem in document["rejected"]]
        assert wheres == ["events[1].event", "events[2].seq", "events[3]"]
        assert document["unchanged"] == "trace"
        assert trace_of(session, isolated_state) == []

    def test_an_evidenced_claim_needs_an_artifact_that_exists(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        absent = {**SUPPORTED, "artifact": "runs/absent.json"}
        code, document, _ = record(session, capsys, absent)
        assert code == 1
        assert "does not exist" in document["rejected"][0]["fix"]
        code, _, _ = record(session, capsys, PLANNED)  # a plan is not checked
        assert code == 0

    def test_a_change_that_breaks_the_claim_law_is_refused(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, PLANNED)
        changed = {"event": "claim-changed", "claim": "scale", "status": "supported"}
        code, document, _ = record(session, capsys, changed)
        assert code == 1
        assert "location" in document["rejected"][0]["fix"]


class TestRepin:
    def test_a_move_moves_the_root_that_claims_resolve_against(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path, tmp_path: Path
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, stage(2), SUPPORTED)
        moved = artifacts.rename(tmp_path / "merged")
        _, document, _ = run(["check", session], capsys)
        assert len(document["missing_artifacts"]) == 1
        move = {"event": "artifacts-moved", "root": str(moved)}
        assert record(session, capsys, move)[0] == 0
        _, document, _ = run(["check", session], capsys)
        assert document["ledger"][0]["exists"] is True
        assert document["missing_artifacts"] == []
        _, document, _ = run(["status", session], capsys)
        assert document["artifacts"] == str(moved)

    def test_a_move_to_a_missing_directory_is_refused(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path, tmp_path: Path
    ) -> None:
        session = opened(capsys, artifacts)
        move = {"event": "artifacts-moved", "root": str(tmp_path / "gone")}
        code, document, _ = record(session, capsys, move)
        assert code == 1
        assert document["rejected"][0]["where"] == "events[0].root"


class TestGates:
    def test_no_stage_past_a_gate_until_the_human_accepts(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, stage(2), SUPPORTED, request("ledger"))
        code, document, _ = record(session, capsys, stage(3))
        assert code == 1
        assert (
            "past the ledger gate, which is pending" in document["rejected"][0]["fix"]
        )
        code, document, _ = record(session, capsys, decide("ledger", "change"))
        assert code == 0
        assert document["gates"]["ledger"] == "change"
        assert document["next"].startswith("change the evidence ledger")
        assert record(session, capsys, stage(3))[0] == 1
        assert (
            record(session, capsys, request("ledger"), decide("ledger", "accept"))[0]
            == 0
        )
        assert record(session, capsys, stage(3))[0] == 0

    def test_an_accepted_gate_points_to_the_next_stage(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        code, document, _ = record(
            session,
            capsys,
            stage(2),
            SUPPORTED,
            request("ledger"),
            decide("ledger", "accept"),
        )
        assert code == 0
        assert document["next"] == "the ledger gate passed; record stage-started 3"

    def test_a_decision_needs_a_pending_request(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        code, document, _ = record(
            session, capsys, stage(2), decide("ledger", "accept")
        )
        assert code == 1
        assert "no pending request" in document["rejected"][0]["fix"]

    def test_restarting_a_gated_stage_reopens_its_gate(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, stage(2), SUPPORTED, request("ledger"))
        record(session, capsys, decide("ledger", "accept"), stage(3), stage(2))
        _, document, _ = run(["status", session], capsys)
        assert document["gates"]["ledger"] == "open"
        assert record(session, capsys, stage(3))[0] == 1

    def test_a_rejection_closes_the_run(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, stage(2), SUPPORTED, request("ledger"))
        assert record(session, capsys, decide("ledger", "reject"))[0] == 0
        code, document, _ = record(
            session, capsys, {"event": "decision", "what": "a", "why": "b"}
        )
        assert code == 1
        assert "closed the run" in document["rejected"][0]["fix"]
        _, document, _ = run(["status", session], capsys)
        assert document["closed_by"] == "ledger"

    def test_the_draft_gate_refuses_planned_claims_and_lost_artifacts(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, stage(2), SUPPORTED, PLANNED, request("ledger"))
        record(session, capsys, decide("ledger", "accept"), stage(8))
        code, document, _ = record(session, capsys, request("draft"))
        assert code == 1
        assert "is to-run" in document["rejected"][0]["fix"]
        removal = {
            "event": "claim-removed",
            "claim": "scale out",
            "reason": "no budget",
        }
        assert record(session, capsys, removal)[0] == 0
        (artifacts / "runs" / "metrics.json").unlink()
        code, document, _ = record(session, capsys, request("draft"))
        assert code == 1
        assert "does not exist" in document["rejected"][0]["fix"]

    def test_a_design_run_accepts_its_prospective_ledger_at_the_plan_gate(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts, verb="design", status="initial")
        code, document, _ = record(session, capsys, stage(1), request("plan"))
        assert code == 1
        assert "as to-run" in document["rejected"][0]["fix"]
        code, document, _ = record(
            session,
            capsys,
            stage(1),
            PLANNED,
            request("plan"),
            decide("plan", "accept"),
        )
        assert code == 0
        assert document["gates"] == {"plan": "accepted"}
        assert document["next"] == "deliver per the output contract"
        assert record(session, capsys, stage(2))[0] == 1


class TestViews:
    def test_check_renders_the_ledger_and_flags_a_lost_artifact(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, stage(2), SUPPORTED)
        (artifacts / "runs" / "metrics.json").unlink()
        code, document, _ = run(["check", session], capsys)
        assert code == 0
        assert document["ledger"][0]["exists"] is False
        assert len(document["missing_artifacts"]) == 1
        assert document["gate"]["name"] == "ledger"
        assert [row["event"] for row in document["since_last_decision"]] == [
            "stage-started",
            "claim-added",
        ]


class TestReplay:
    """The trace is authoritative: a line the script would not have written
    stops every command with the line named."""

    STAMP = '{"t": "2026-01-01T00:00:00+00:00", "run": "RUN", '

    @pytest.mark.parametrize(
        ("line", "message"),
        [
            ("{not json", "not JSON"),
            (STAMP + '"event": "nap"}', "trace event 2"),
            (
                STAMP.replace("RUN", "other") + '"event": "stage-started", "stage": 3}',
                "run is 'other'",
            ),
            (STAMP + '"event": "stage-started", "stage": 8}', "past the ledger gate"),
        ],
    )
    def test_a_hand_edited_line_is_an_authoritative_defect(
        self,
        capsys: pytest.CaptureFixture[str],
        artifacts: Path,
        isolated_state: Path,
        line: str,
        message: str,
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, stage(2))
        path = isolated_state / "state/btm-skills/draft-paper/sessions" / session
        with (path / "trace.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(line.replace("RUN", session) + "\n")
        code, _, err = run(["status", session], capsys)
        assert code == 1
        assert message in err


CORPUS_ROWS = [
    {
        "key": "doi:10.1/a",
        "title": "Bandit prompt routing",
        "year": 2021,
        "authors": ["A. Author"],
        "doi": "10.1/a",
        "status": "included",
        "read_level": "abstract",
        "found_by": ["s1"],
    },
    {
        "key": "arxiv:2401.00001",
        "title": "Later work",
        "arxiv_id": "2401.00001",
        "status": "candidate",
    },
]


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """A lit-review session directory, laid out as lit-review writes it."""
    root = tmp_path / "lit"
    root.mkdir()
    (root / "protocol.json").write_text("{}", encoding="utf-8")
    (root / "papers.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in CORPUS_ROWS), encoding="utf-8"
    )
    return root


def cite_event(ref: str) -> dict[str, Any]:
    return {"event": "citation-added", "ref": ref, "sentence": f"as {ref} shows"}


class TestCorpus:
    def test_link_records_the_corpus_and_status_shows_it(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path, corpus: Path
    ) -> None:
        session = opened(capsys, artifacts)
        code, document, _ = run(["attach", session, "--corpus", str(corpus)], capsys)
        assert code == 0
        assert document["records"] == 2
        _, status, _ = run(["status", session], capsys)
        assert status["corpus"] == str(corpus / "papers.jsonl")
        assert status["connections"] == [
            {"skill": "lit-review", "session": "lit", "path": str(corpus)}
        ]

    def test_start_takes_a_project_status_shows(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        code, document, err = run(
            [
                *("start", "tail latency", "--verb", "build", "--format", "full"),
                *("--status", "partial", "--venue", "v", "--model", "m"),
                *("--artifacts", str(artifacts), "--project", "ste-tax"),
            ],
            capsys,
        )
        assert code == 0, err
        _, status, _ = run(["status", document["session"]], capsys)
        assert status["project"] == "ste-tax"

    def test_check_resolves_each_citation_against_the_attached_corpus(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path, corpus: Path
    ) -> None:
        session = opened(capsys, artifacts)
        run(["attach", session, "--corpus", str(corpus)], capsys)
        code, _, err = record(
            session,
            capsys,
            cite_event("10.1/A"),
            cite_event("arXiv:2401.00001"),
            cite_event("10.9/elsewhere"),
        )
        assert code == 0, err
        _, document, _ = run(["check", session], capsys)
        rows = document["citations"]["rows"]
        assert [row["key"] for row in rows] == [
            "doi:10.1/a",
            "arxiv:2401.00001",
            None,
        ]
        assert rows[0]["record"]["title"] == "Bandit prompt routing"
        assert "record" not in rows[2]
        assert document["citations"]["unresolved"] == ["10.9/elsewhere"]

    def test_without_a_corpus_every_citation_is_unresolved(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path
    ) -> None:
        session = opened(capsys, artifacts)
        record(session, capsys, cite_event("10.1/a"))
        _, document, _ = run(["check", session], capsys)
        assert document["citations"]["corpus"] is None
        assert document["citations"]["unresolved"] == ["10.1/a"]

    def test_a_vanished_corpus_signals_rather_than_refusing(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path, corpus: Path
    ) -> None:
        session = opened(capsys, artifacts)
        run(["attach", session, "--corpus", str(corpus)], capsys)
        record(session, capsys, cite_event("10.1/a"))
        (corpus / "papers.jsonl").unlink()
        code, document, err = run(["check", session], capsys)
        assert code == 0
        assert "attached corpus unreadable" in err
        assert document["citations"]["unresolved"] == ["10.1/a"]

    def test_cite_reads_the_session_link_before_any_index(
        self, capsys: pytest.CaptureFixture[str], artifacts: Path, corpus: Path
    ) -> None:
        session = opened(capsys, artifacts)
        run(["attach", session, "--corpus", str(corpus)], capsys)
        code, document, _ = run(["cite", "10.1/a", "--session", session], capsys)
        assert code == 0
        assert (document["key"], document["source"]) == ("doi:10.1/a", "lit")
