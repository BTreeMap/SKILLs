"""The offline command surface end to end, against a session directory."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from btm_lit_review.cli import main
from btm_lit_review.paper import candidate
from btm_lit_review.session import Session, load_papers, save_papers


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test owns its own state root, so none can see real lore."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))


def run(argv, capsys, stdin: str | None = None, monkeypatch=None):
    """Run one command and return (exit code, parsed stdout, stderr)."""
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", __import__("io").StringIO(stdin))
    code = main(argv)
    captured = capsys.readouterr()
    document = json.loads(captured.out) if captured.out.strip() else None
    return code, document, captured.err


def paper(title, doi, abstract=None, **decisions):
    built = candidate(
        title=title,
        year=2024,
        authors=("A", "B"),
        venue="venue",
        doi=doi,
        arxiv_id=None,
        openalex_id=None,
        cited_by_count=5,
        abstract=abstract,
        pdf_url=None,
        landing_url=None,
    )
    return replace(built, **({"found_by": ("s1",)} | decisions))


@pytest.fixture
def session(tmp_path, capsys):
    root = tmp_path / "review"
    code, document, _ = run(["init", str(root), "--question", "q"], capsys)
    assert code == 0
    assert document["dir"] == str(root)
    built = Session(root)
    protocol = json.loads(built.protocol_path.read_text())
    protocol["criteria"] = {"include": ["on topic"], "exclude": ["off topic"]}
    built.protocol_path.write_text(json.dumps(protocol))
    corpus = [
        paper("Bandit routing survey", "10.1/a", abstract="a survey"),
        paper(
            "GFlowNet sampler",
            "10.1/b",
            abstract="sampler",
            status="included",
            read_level="full-text",
            found_by=("s2",),
        ),
        paper("Cooking blog", "10.1/c"),
    ]
    save_papers(built, {p.key: p for p in corpus})
    built.log_path.write_text(
        '{"id": "s1", "command": "search"}\n{"id": "s2", "command": "search"}\n'
    )
    return built


class TestScreen:
    def test_a_rule_screens_candidates_and_records_itself(self, session, capsys):
        code, document, _ = run(
            [
                "screen",
                str(session.root),
                "--match",
                "cooking|blog",
                "--exclude",
                "--reason",
                "off topic",
            ],
            capsys,
        )
        assert code == 0
        assert document["rule"] == "r1"
        assert document["matched"] == 1
        _, shown, _ = run(["show", str(session.root), "--status", "excluded"], capsys)
        assert shown["papers"][0]["key"] == "doi:10.1/c"
        rule = json.loads(session.notebook_path.read_text().splitlines()[0])
        assert rule["matched"] == ["doi:10.1/c"]

    def test_decided_papers_are_never_touched(self, session, capsys):
        code, document, _ = run(
            [
                "screen",
                str(session.root),
                "--match",
                "sampler",
                "--on",
                "abstract",
                "--exclude",
                "--reason",
                "r",
            ],
            capsys,
        )
        assert code == 0
        assert document["matched"] == 0


class TestShow:
    def test_match_fields_and_tsv_compose(self, session, capsys):
        code = main(
            [
                "show",
                str(session.root),
                "--match",
                "bandit",
                "--fields",
                "key,year",
                "--format",
                "tsv",
            ]
        )
        out = capsys.readouterr().out
        assert code == 0
        assert out.splitlines() == ["key\tyear", "doi:10.1/a\t2024"]

    def test_keys_select_exactly_and_name_the_missing(self, session, capsys):
        code, document, err = run(
            ["show", str(session.root), "--keys", "doi:10.1/b,doi:10.1/z"], capsys
        )
        assert code == 0
        assert [p["key"] for p in document["papers"]] == ["doi:10.1/b"]
        assert "doi:10.1/z" in err


BATCH = {
    "findings": [{"claim": "sampling works", "support": ["doi:10.1/b"]}],
    "gaps": [
        {
            "statement": "nothing combines them",
            "probes": ["s2"],
            "watch": "combined",
        }
    ],
}


class TestNoteAndBrief:
    def admit(self, session, tmp_path, capsys):
        batch_file = tmp_path / "round.json"
        batch_file.write_text(json.dumps(BATCH))
        return run(["note", str(session.root), "--file", str(batch_file)], capsys)

    def test_a_clean_batch_is_admitted_with_a_receipt(self, session, tmp_path, capsys):
        code, document, _ = self.admit(session, tmp_path, capsys)
        assert code == 0
        assert document["admitted"] == {"findings": ["f1"], "gaps": ["g1"]}

    def test_a_broken_batch_returns_every_fix_and_changes_nothing(
        self, session, capsys, monkeypatch
    ):
        bad = {"findings": [{"claim": "", "support": ["ghost"]}], "junk": []}
        code, document, _ = run(
            ["note", str(session.root)], capsys, json.dumps(bad), monkeypatch
        )
        assert code == 1
        assert len(document["rejected"]) == 3
        assert document["notebook"] == "unchanged"
        assert not session.notebook_path.exists()

    def test_brief_derives_verdicts_and_tracks_drift(self, session, tmp_path, capsys):
        self.admit(session, tmp_path, capsys)
        code, first, _ = run(["brief", str(session.root)], capsys)
        assert code == 0
        assert first["drift"] == {"since": None}
        assert first["findings"][0]["state"] == "supported"
        assert first["unextracted"] == ["doi:10.1/b"]
        late = paper("Combined system", "10.1/d", abstract="combined", found_by=("s9",))
        papers = load_papers(session)
        papers[late.key] = late
        save_papers(session, papers)
        code, second, err = run(["brief", str(session.root)], capsys)
        assert second["drift"]["new_papers"] == ["doi:10.1/d"]
        assert second["gaps"][0]["state"] == "challenged"
        assert "challenged gaps: g1" in err


class TestPadAndDraft:
    def test_extraction_jots_are_recognized_with_advisories(self, session, capsys):
        code, receipt, err = run(
            ["jot", str(session.root), '{"kind": "extraction", "key": "10.1/zzz"}'],
            capsys,
        )
        assert code == 0
        assert receipt["jotted"] == "j1"
        assert "not a corpus paper" in err

    def test_cite_check_judges_the_draft(self, session, tmp_path, capsys):
        draft = tmp_path / "report.md"
        draft.write_text("Sampling works [1]; phantom [4].")
        code, report, err = run(
            ["cite-check", str(session.root), "--draft", str(draft)], capsys
        )
        assert code == 1
        assert any("never assigned" in p for p in report["problems"])
        assert report["markers"]["[1]"]["key"] == "doi:10.1/b"
        assert "citation problem" in err


class TestSchema:
    def test_every_record_shape_is_printed(self, capsys):
        code, document, _ = run(["schema"], capsys)
        assert code == 0
        assert {"paper", "note_batch", "pad", "search_log", "exit_codes"} <= set(
            document
        )
