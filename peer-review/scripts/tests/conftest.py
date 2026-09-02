"""Shared fixtures: an isolated state root, a small paper, a small corpus."""

from __future__ import annotations

import json

import pytest

from btm_peer_review.text import PaperText, parse_pages

PAPER = """# Extracted from paper.pdf

## PDF page 1

Adaptive Prompt Routing
Jane Doe jane@example.edu
Abstract. We propose AdaRoute, a router that improves accuracy by 12 points
over strong baselines on three benchmarks. Our method is the first to combine
bandits with prompt selection.

## PDF page 2

3 Experiments
We report the best run over five seeds. Baselines were tuned with default
hyperparameters. Table 1 shows accuracy without error bars.

## PDF page 3

6 Limitations
Our evaluation covers English only. We did not compare against
retrieval-based routers.

References
[1] Someone 2020.
"""

CORPUS = [
    {
        "key": "doi:10.1/a",
        "doi": "10.1/a",
        "arxiv_id": None,
        "year": 2021,
        "title": "Bandit prompt routing",
        "status": "included",
    },
    {
        "key": "doi:10.1/b",
        "doi": "10.1/b",
        "arxiv_id": "2401.00001",
        "year": 2027,
        "title": "Later work",
        "status": "candidate",
    },
    {
        "key": "title:undated router",
        "year": None,
        "title": "Undated",
        "status": "candidate",
    },
]


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "state"))
    return tmp_path


@pytest.fixture
def paper_text():
    return PaperText(parse_pages(PAPER))


@pytest.fixture
def paper_file(tmp_path):
    path = tmp_path / "paper.txt"
    path.write_text(PAPER, encoding="utf-8")
    return path


@pytest.fixture
def corpus_dir(tmp_path):
    root = tmp_path / "lit"
    root.mkdir()
    (root / "protocol.json").write_text("{}")
    (root / "papers.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in CORPUS), encoding="utf-8"
    )
    return root
