"""The ste-tax release this skill reads: download, digest gate, and load.

One release is a manifest plus the artifacts it lists, served by jsDelivr
from an immutable git tag. Each artifact sits in the kernel cache under a
slot keyed by `<tag>/<path>`; the manifest is written last, so its presence
marks a complete fetch. Every load re-hashes the file: a mismatch deletes
it and fails with exit 2, so the next run refetches and heals.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import TypeVar

import httpx

from btm_asd_ste100.records import Artifact, Manifest
from btm_corekit import (
    CommandError,
    Model,
    UpstreamError,
    cache_slot,
    download,
    get_bytes,
    parse_model,
    signal,
    write_atomic,
)

SKILL = "asd-ste100"
VERSION = "v0.1.0"
BASE = "https://cdn.jsdelivr.net/gh/RadonSys/ste-tax@{version}/"
MANIFEST = "data/manifest.json"
MANIFEST_CAP = 64 * 1024
TAG = re.compile(r"v\d+\.\d+\.\d+")

W = TypeVar("W", bound=Model)


def tag(raw: str) -> str:
    """A release tag is `vMAJOR.MINOR.PATCH`; anything else names no release."""
    if not TAG.fullmatch(raw):
        raise CommandError(
            f"--version {raw!r} is no release tag; write it like {VERSION}"
        )
    return raw


def url_of(version: str, path: str) -> str:
    return BASE.format(version=version) + path


def slot_of(version: str, path: str) -> Path:
    return cache_slot(SKILL, f"{version}/{path}", ".json")


def fetch(client: httpx.Client, version: str) -> Manifest:
    """Download the manifest and every artifact it lists, gating each on its
    digest; write the manifest last. Cost: one request per artifact."""
    blob = get_bytes(client, url_of(version, MANIFEST), MANIFEST_CAP)
    try:
        manifest = parse_model(Manifest, json.loads(blob), f"{version} manifest")
    except (json.JSONDecodeError, CommandError) as err:
        raise UpstreamError(
            f"{version} manifest is not a ste-tax manifest: {err}"
        ) from err
    for artifact in manifest.artifacts:
        target = slot_of(version, artifact.path)
        download(
            client,
            url_of(version, artifact.path),
            target,
            2 * artifact.bytes + MANIFEST_CAP,
        )
        verified(target, artifact, version)
    manifest_slot = slot_of(version, MANIFEST)
    manifest_slot.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(manifest_slot, blob.decode("utf-8"))
    return manifest


def verified(target: Path, artifact: Artifact, version: str) -> bytes:
    """The artifact's bytes when size and SHA-256 match the manifest. On a
    mismatch the file is deleted and the run fails, so a rerun refetches."""
    blob = target.read_bytes()
    if (
        len(blob) != artifact.bytes
        or hashlib.sha256(blob).hexdigest() != artifact.sha256
    ):
        target.unlink(missing_ok=True)
        raise UpstreamError(
            f"{version} {artifact.path}: digest differs from the manifest; "
            "the corrupt copy was deleted, rerun to refetch"
        )
    return blob


def cached(version: str) -> Manifest | None:
    """The cached manifest when it and every artifact it lists are present;
    a missing piece (a deleted corrupt copy) reads as no cache."""
    slot = slot_of(version, MANIFEST)
    if not slot.is_file():
        return None
    manifest = parse_model(
        Manifest, json.loads(slot.read_bytes()), f"cached {version} manifest"
    )
    if all(slot_of(version, a.path).is_file() for a in manifest.artifacts):
        return manifest
    return None


def ensure(client: httpx.Client, version: str) -> Manifest:
    """The cached release, fetched first when absent or incomplete."""
    manifest = cached(version)
    if manifest is not None:
        return manifest
    signal(f"no complete cache of ste-tax {version}; fetching it first")
    try:
        return fetch(client, version)
    except CommandError as err:  # a 404 too: a fresh tag can lag on the CDN
        why = f"cannot fetch ste-tax {version}, which this run needs: {err}"
        raise UpstreamError(why) from err


def load(manifest: Manifest, version: str, name: str, model: type[W]) -> W:
    """Decode one listed artifact after re-checking its digest."""
    path = f"data/{name}"
    artifact = next((a for a in manifest.artifacts if a.path == path), None)
    if artifact is None:
        raise UpstreamError(f"{version} manifest lists no {path}")
    blob = verified(slot_of(version, path), artifact, version)
    return parse_model(model, json.loads(blob), f"{version} {path}")
