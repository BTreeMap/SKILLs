"""Citation resolution: every DOI in the corpus checked against its registrar."""

from __future__ import annotations

import argparse
import difflib
import time
from typing import Any

from btm_corekit import JSON, CommandError, UpstreamError, emit, signal
from btm_lit_review.constants import (
    COURTESY_PAUSE_SECONDS,
    CROSSREF_WORKS,
    HTTP_OK,
    REDIRECT_STATUSES,
    TITLE_MATCH_FLOOR,
)
from btm_lit_review.http import doi_resolution_status, http_get_json
from btm_lit_review.paper import Paper, clean_text, normalize_title
from btm_lit_review.session import load_papers, open_session


def verify_one(paper: Paper) -> dict[str, JSON]:
    """One row per paper; an unreachable registrar is recorded in the row, so
    one bad moment upstream never discards the rows already collected."""
    result: dict[str, Any] = {"key": paper.key, "title": paper.title}
    try:
        _verify_into(result, paper)
    except UpstreamError as err:
        result["error"] = str(err)
        signal(f"{paper.key}: {err}")
    time.sleep(COURTESY_PAUSE_SECONDS)
    return result


def _verify_into(result: dict[str, Any], paper: Paper) -> None:
    if paper.doi:
        status = doi_resolution_status(paper.doi)
        result["doi_resolves"] = status in REDIRECT_STATUSES or status == HTTP_OK
        result["doi_http_status"] = status
        try:
            message = http_get_json(f"{CROSSREF_WORKS}/{paper.doi}").get("message")
        except CommandError:
            message = None
        if message and message.get("title"):
            registered = clean_text(" ".join(message["title"])) or ""
            ratio = difflib.SequenceMatcher(
                None, normalize_title(paper.title), normalize_title(registered)
            ).ratio()
            result["crossref_title_match"] = round(ratio, 2)
            if ratio < TITLE_MATCH_FLOOR:
                signal(
                    f"{paper.key}: corpus title diverges from Crossref record "
                    f"({registered!r}); check for a mangled citation"
                )
        else:
            result["crossref_title_match"] = None
            signal(
                f"{paper.key}: no Crossref metadata (DataCite DOIs such as "
                "arXiv resolve but are not title-checked here)"
            )
    elif paper.arxiv_id:
        result["doi_resolves"] = None
        result["identity"] = f"arXiv:{paper.arxiv_id} (no DOI; not registrar-checked)"
    else:
        result["doi_resolves"] = None
        result["identity"] = "title-only record; verify against the source by hand"


def cmd_verify(args: argparse.Namespace) -> int:
    session = open_session(args.session)
    papers = load_papers(session)
    wanted = set(args.keys.split(",")) if args.keys else None
    included = [
        paper
        for key, paper in papers.items()
        if paper.status == "included" and (wanted is None or key in wanted)
    ]
    if not included:
        raise CommandError("no included papers to verify; screen the corpus first")
    unread = [paper.key for paper in included if paper.read_level == "none"]
    if unread:
        signal(f"included but unread (read_level none): {', '.join(unread)}")
    results = [verify_one(paper) for paper in included]
    broken = [r["key"] for r in results if r.get("doi_resolves") is False]
    emit(
        {
            "checked": len(results),
            "broken_dois": broken,
            "errors": [r["key"] for r in results if "error" in r],
            "results": results,
        }
    )
    return 0
