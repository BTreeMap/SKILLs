"""The `report` command end to end through `main`: placement, the Invariant 4
source rule, and the all-at-once rejection."""

from __future__ import annotations

import json
from typing import Any

import pytest
from btm_fact_check.cli import main

OWNER = {
    "quote": "Rate limit: 100 requests per minute.",
    "url": "https://docs.example.org/limits",
    "publisher": "Example Org",
    "published": None,
    "accessed": "2026-10-08",
}
PRESS = {
    "quote": "Example Org caps its API at 100 requests a minute.",
    "url": "https://news.example.net/a",
    "publisher": "Example News",
    "accessed": "2026-10-08",
}
PROBE = {
    "probe": "GET https://api.example.org/v1/items",
    "status": 200,
    "keys": ["items", "x-ratelimit-limit"],
    "accessed": "2026-10-08",
}


def claim(ident: str, **fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": ident,
        "claim": f"claim {ident}",
        "span": {"file": "doc.md", "lines": "3-4", "quote": f"text {ident}"},
        "type": "spec",
        "verdict": "supported",
        "confidence": "high",
        "evidence": [OWNER],
    }
    return base | fields


def state(*claims: dict[str, Any], **fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "constraints": ["never edit without approval"],
        "file": "doc.md",
        "claim_time": "2026-01-01",
        "branch": "sequential",
        "claims": list(claims),
    }
    return base | fields


def run(tmp_path, capsys, document: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    path = tmp_path / "factcheck-state.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    code = main(["report", "--state:file", str(path)])
    out = capsys.readouterr().out
    return code, json.loads(out) if out else {}


def test_sections_follow_verdict_and_correction(tmp_path, capsys):
    code, doc = run(
        tmp_path,
        capsys,
        state(
            claim("c-01"),
            claim(
                "c-02",
                verdict="contradicted",
                evidence=[OWNER, PRESS],
                correction="100 requests per minute",
            ),
            claim("c-03", verdict="conflicting", evidence=[OWNER, PRESS]),
            claim("c-04", verdict="outdated", confidence="low"),
            claim("c-05", verdict="unverifiable", evidence=[], notes="paywalled"),
        ),
    )
    assert code == 0
    report = doc["report"]
    corrections, rest = report.split("### Needs your judgment")
    judgment, rest = rest.split("### Verified accurate")
    accurate, unverified = rest.split("### Unverifiable / insufficient evidence")
    assert "c-02" in corrections and "> 100 requests per minute" in corrections
    assert "c-03" in judgment and "c-04" in judgment
    assert "No correction proposed." in judgment
    assert "- c-01: claim c-01 (Example Org, https://docs.example.org/limits)" in (
        accurate
    )
    assert "- c-05: claim c-05 (paywalled)" in unverified
    assert "### Side findings" not in report
    assert doc["verdicts"]["supported"] == 1 and doc["claims"] == 5
    assert "Verdicts: supported 1, contradicted 1, outdated 1, conflicting 1," in report


def test_spec_correction_rests_on_owner_plus_probe(tmp_path, capsys):
    code, doc = run(
        tmp_path,
        capsys,
        state(
            claim(
                "c-01",
                verdict="contradicted",
                evidence=[OWNER, PROBE],
                correction="100 requests per minute",
            )
        ),
    )
    assert code == 0
    assert (
        "- live probe GET https://api.example.org/v1/items returned 200, "
        "keys items, x-ratelimit-limit (accessed 2026-10-08)"
    ) in doc["report"]
    assert "Rests on the owner plus the live probe." in doc["report"]


@pytest.mark.parametrize(
    ("ctype", "evidence"),
    [
        ("statistic", [OWNER, PROBE]),  # the exception is spec only
        ("spec", [OWNER, OWNER | {"url": "https://docs.example.org/b"}]),
    ],
)
def test_correction_without_independent_sources_is_refused(
    tmp_path, capsys, ctype, evidence
):
    code, doc = run(
        tmp_path,
        capsys,
        state(
            claim(
                "c-01",
                type=ctype,
                verdict="contradicted",
                evidence=evidence,
                correction="x",
            )
        ),
    )
    assert code == 1
    assert [p["where"] for p in doc["rejected"]] == ["claims[0].correction"]


def test_every_problem_comes_back_in_one_verdict(tmp_path, capsys):
    code, doc = run(
        tmp_path,
        capsys,
        state(
            claim("c-01", verdict=None, confidence=None),
            claim("c-01", verdict="supported", evidence=[PROBE]),
            claim(
                "c-03", verdict="conflicting", evidence=[OWNER, PRESS], correction="x"
            ),
            claim("c-04", verdict="unverifiable", evidence=[]),
        ),
    )
    assert code == 1
    assert sorted(p["where"] for p in doc["rejected"]) == [
        "claims[0].confidence",
        "claims[0].id",
        "claims[0].verdict",
        "claims[1].evidence",
        "claims[1].id",
        "claims[2].correction",
        "claims[3].notes",
    ]
    assert doc["unchanged"] == "nothing: report writes no state"


def test_evidence_decodes_by_field_presence(tmp_path, capsys):
    broken = PROBE | {"status": "ok"}
    code, doc = run(tmp_path, capsys, state(claim("c-01", evidence=[OWNER, broken])))
    assert code == 1
    assert [p["where"] for p in doc["rejected"]] == [
        "claims[0].evidence[1].probe.status"
    ]


def test_side_findings_render_with_their_evidence(tmp_path, capsys):
    finding = {"finding": "The docs list no AMD path.", "evidence": [OWNER]}
    code, doc = run(tmp_path, capsys, state(claim("c-01"), side_findings=[finding]))
    assert code == 0
    assert doc["report"].endswith(
        '### Side findings\n\n- The docs list no AMD path. "Rate limit: 100 '
        'requests per minute." (Example Org, published unknown, accessed '
        "2026-10-08, https://docs.example.org/limits)\n"
    )


def test_malformed_json_is_a_rejection(tmp_path, capsys):
    path = tmp_path / "factcheck-state.json"
    path.write_text("{", encoding="utf-8")
    assert main(["report", "--state:file", str(path)]) == 1
    assert "make the state valid JSON" in capsys.readouterr().err


def test_cite_gives_a_scholarly_source_one_citable_record(tmp_path, capsys):
    """A named corpus answers without a request; report is untouched."""
    session = tmp_path / "lit"
    session.mkdir()
    (session / "papers.jsonl").write_text(
        json.dumps({"key": "doi:10.1/a", "title": "T", "doi": "10.1/a"}) + "\n",
        encoding="utf-8",
    )
    assert main(["cite", "10.1/a", "--corpus", str(session)]) == 0
    document = json.loads(capsys.readouterr().out)
    assert (document["key"], document["source"]) == ("doi:10.1/a", "lit")
