"""The command surface end to end."""

from __future__ import annotations

import json

from btm_peer_review.cli import main


def run(argv, capsys):
    code = main(argv)
    captured = capsys.readouterr()
    document = json.loads(captured.out) if captured.out.strip() else None
    return code, document, captured.err


def started(capsys, paper_file, level="full") -> str:
    code, document, _ = run(
        [
            "init",
            "ada route",
            "--title",
            "AdaRoute",
            "--date",
            "2026-03",
            "--level",
            level,
        ],
        capsys,
    )
    assert code == 0
    session = document["session"]
    code, document, err = run(["ingest", session, "--text", str(paper_file)], capsys)
    assert code == 0 and document["pages"] == 3 and document["limitations_section"]
    assert "author block" in err
    return session


def batch(tmp_path, payload) -> str:
    path = tmp_path / "round.json"
    path.write_text(json.dumps(payload))
    return str(path)


class TestFlow:
    def test_init_rejects_a_bad_date(self, capsys):
        code, _, err = run(
            ["init", "ada route", "--title", "t", "--date", "March"], capsys
        )
        assert code == 1 and "YYYY" in err

    def test_note_check_cite_check_and_clean(
        self, capsys, paper_file, corpus_dir, tmp_path
    ):
        session = started(capsys, paper_file)
        code, document, _ = run(["link", session, "--corpus", str(corpus_dir)], capsys)
        assert code == 0 and document["records"] == 3 and document["postdating"] == 1
        payload = {
            "claims": [
                {
                    "kw": ["first", "combine"],
                    "verbatim": "Our method is the first to combine bandits "
                    "with prompt selection.",
                }
            ],
            "objections": [
                {
                    "kw": ["not", "first"],
                    "kind": "first",
                    "severity": "major",
                    "text": "Bandit routing predates it.",
                    "claim": "first combine",
                    "anchors": ["the first to combine bandits"],
                    "prior": ["doi:10.1/a"],
                },
                {
                    "kw": ["error", "bars"],
                    "kind": "variance",
                    "severity": "minor",
                    "text": "No spread.",
                    "missing": "error bars for Table 1",
                },
            ],
            "walks": [
                {"bank": bank}
                for bank in ("claims", "design", "analysis", "limitations", "novelty")
            ],
        }
        code, document, _ = run(
            ["note", session, "--file", batch(tmp_path, payload)], capsys
        )
        assert code == 0
        assert document["admitted"] == {"claim": 1, "objection": 2, "walk": 5}
        code, document, err = run(["check", session], capsys)
        assert code == 0
        assert document["recommendation"]["verdict"] == "major revision"
        assert document["coverage"]["confidence"] == "high"
        assert [v["standing"] for v in document["objections"]] == [
            "grounded",
            "grounded",
        ]
        assert "not yet walked" not in err
        draft = tmp_path / "review.md"
        draft.write_text("Claim [C1] is contested by [O1]. Minor: [O2].")
        code, document, _ = run(["cite-check", session, "--draft", str(draft)], capsys)
        assert code == 0 and document["problems"] == []
        draft.write_text("Only [O2].")
        code, document, err = run(
            ["cite-check", session, "--draft", str(draft)], capsys
        )
        assert code == 1 and "[O1] is a grounded major" in document["problems"][0]
        code, document, _ = run(["clean", session], capsys)
        assert code == 0 and document["bytes_freed"] > 0

    def test_a_rejected_note_leaves_the_ledger_unchanged(
        self, capsys, paper_file, tmp_path
    ):
        session = started(capsys, paper_file)
        payload = {
            "objections": [
                {
                    "kw": ["a", "b"],
                    "kind": "control",
                    "severity": "major",
                    "text": "x",
                    "anchors": ["nothing like this appears in the paper"],
                }
            ]
        }
        code, document, _ = run(
            ["note", session, "--file", batch(tmp_path, payload)], capsys
        )
        assert code == 1 and document["ledger"] == "unchanged"
        code, document, _ = run(["status", session], capsys)
        assert code == 0 and document["objections"] == {}

    def test_reingest_signals_and_unanchors(self, capsys, paper_file, tmp_path):
        session = started(capsys, paper_file)
        payload = {
            "objections": [
                {
                    "kw": ["best", "run"],
                    "kind": "selective",
                    "severity": "major",
                    "text": "x",
                    "anchors": ["We report the best run over five seeds"],
                }
            ]
        }
        assert (
            run(["note", session, "--file", batch(tmp_path, payload)], capsys)[0] == 0
        )
        other = tmp_path / "v2.txt"
        other.write_text("## PDF page 1\n\nWe report the mean over five seeds.\n")
        code, _, err = run(["ingest", session, "--text", str(other)], capsys)
        assert code == 0 and "re-derives" in err
        code, document, err = run(["check", session], capsys)
        assert document["objections"][0]["standing"] == "unanchored"
        assert "lost their grounding" in err

    def test_lite_level_needs_only_two_banks(self, capsys, paper_file, tmp_path):
        session = started(capsys, paper_file, level="lite")
        payload = {"walks": [{"bank": "claims"}, {"bank": "limitations"}]}
        assert (
            run(["note", session, "--file", batch(tmp_path, payload)], capsys)[0] == 0
        )
        _, document, err = run(["check", session], capsys)
        assert document["coverage"]["unwalked"] == [] and "not yet walked" not in err

    def test_pad_and_schema(self, capsys, paper_file):
        session = started(capsys, paper_file)
        code, document, _ = run(
            ["jot", session, '{"kind": "injection", "page": 2}'], capsys
        )
        assert code == 0 and document["jotted"] == "j1"
        code, document, _ = run(["recall", session, "--kind", "injection"], capsys)
        assert document["shown"] == 1
        _, document, _ = run(["schema"], capsys)
        assert "novelty" in document["banks"]
