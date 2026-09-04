"""Generated content: plugin manifests and the README and AGENTS listings."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from btm_repo_gate.conventions import BRAND, MARKETPLACE
from btm_repo_gate.listings import LISTINGS
from btm_repo_gate.repairs import Finding, WriteText
from btm_repo_gate.snapshot import Absent, Parsed, Repo, Unreadable


def rule_manifest(repo: Repo) -> Iterator[Finding]:
    """The manifests publish this repository under one brand and declare every
    skill path, which is what makes discovery declared rather than a fallback
    scan. Names and the skill list are functions of `BRAND` and the tree, so
    drift is repaired; absent or unreadable content needs a person."""
    for path in sorted(repo.manifests):
        match repo.manifests[path]:
            case Absent():
                yield Finding("manifest", str(path), "manifest is missing")
            case Unreadable(reason):
                yield Finding("manifest", str(path), f"unreadable manifest: {reason}")
            case Parsed(doc):
                yield from _manifest_findings(path, doc, repo.skills)


def _manifest_findings(
    path: Path, doc: dict[str, Any], skills: frozenset[str]
) -> Iterator[Finding]:
    canonical = json.loads(json.dumps(doc))  # independent copy; `doc` stays pure
    reasons: list[str] = []
    if canonical.get("name") != BRAND:
        canonical["name"] = BRAND
        reasons.append(f"name set to {BRAND!r}")
    if path == MARKETPLACE:
        plugins = canonical.get("plugins")
        if not (isinstance(plugins, list) and plugins and isinstance(plugins[0], dict)):
            yield Finding(
                "manifest", str(path), "plugins[0] is not an object; restructure it"
            )
            return
        entry = plugins[0]
        if entry.get("name") != BRAND:
            entry["name"] = BRAND
            reasons.append(f"plugin name set to {BRAND!r}")
        declared = [f"./{skill}" for skill in sorted(skills)]
        if entry.get("skills") != declared:
            entry["skills"] = declared
            reasons.append("skill list regenerated from the tree")
    if reasons:
        yield Finding(
            "manifest",
            str(path),
            "; ".join(reasons),
            WriteText(path, json.dumps(canonical, indent=2) + "\n"),
        )


def rule_listings(repo: Repo) -> Iterator[Finding]:
    """Every skill appears in each listing, in order. Ordering is a total
    function of the entries, so it is repaired; a missing entry needs a written
    summary, so it is not."""
    for path, extract in LISTINGS:
        text = repo.texts.get(path)
        if text is None:
            yield Finding("listing", str(path), "document is missing")
            continue
        listing = extract(text)
        if listing is None:
            yield Finding("listing", str(path), "no skill listing found")
            continue
        named = listing.named
        for missing in sorted(repo.skills - set(named)):
            yield Finding("listing", str(path), f"no entry for skill {missing!r}")
        for unknown in sorted(set(named) - repo.skills):
            yield Finding("listing", str(path), f"entry {unknown!r} names no skill")
        if named != sorted(named):
            yield Finding(
                "listing",
                str(path),
                "skill entries are not in alphabetical order",
                WriteText(path, listing.sorted_text()),
            )
