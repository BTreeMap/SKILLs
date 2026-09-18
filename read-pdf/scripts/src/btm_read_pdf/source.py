"""Where a PDF comes from: a local path, or a URL materialized through a cache."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from btm_corekit import CommandError, build_client, cache_slot, signal, stream

TIMEOUT_SECONDS = 30
DEFAULT_MAX_BYTES = 200 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class LocalPdf:
    path: Path  # is_file() held at construction


@dataclass(frozen=True, slots=True)
class RemotePdf:
    url: str  # scheme is http or https


Source = LocalPdf | RemotePdf


def parse_source(raw: str) -> Source:
    """The one boundary an untrusted input argument crosses."""
    if raw.startswith(("http://", "https://")):
        return RemotePdf(raw)
    path = Path(raw)
    if not path.is_file():
        raise CommandError(f"PDF file not found: {path}")
    return LocalPdf(path)


def materialize(
    source: Source,
    max_bytes: int = DEFAULT_MAX_BYTES,
    transport: httpx.BaseTransport | None = None,
) -> tuple[Path, str]:
    """Eliminate a Source into (local path, display name).

    A URL downloads once per cache lifetime, keyed by its digest; deleting the
    cached file is the refresh. The display name of a remote source is the URL
    itself, so extractions cite true provenance.
    """
    match source:
        case LocalPdf(path):
            return path, path.name
        case RemotePdf(url):
            target = cache_slot("read-pdf", url, ".pdf")
            if target.is_file():
                signal(f"cached: reusing {target}; clean drops the cache")
            else:
                _fetch(url, target, max_bytes, transport)
            return target, url


def _fetch(
    url: str, target: Path, max_bytes: int, transport: httpx.BaseTransport | None
) -> None:
    """Stream to a per-process partial, sniff the PDF magic, rename on success.

    The pid in the partial name keeps concurrent fetches of one URL from
    interleaving; os.replace makes the last completed writer win, and both
    wrote the same URL. The magic check gates the cache: a paywall's HTML
    page fails here once rather than poisoning the cache.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{target.name}.{os.getpid()}.partial")
    client = build_client("read-pdf", read_timeout=TIMEOUT_SECONDS, transport=transport)
    try:
        with client, partial.open("wb") as out:
            stream(
                client,
                url,
                out.write,
                max_bytes,
                remedy="pass --max-bytes to raise the cap",
            )
        with partial.open("rb") as head:
            # The spec tolerates up to 1024 bytes of preamble before %PDF-.
            if b"%PDF-" not in head.read(1024):
                raise CommandError(f"fetched content is not a PDF: {url}")
    except CommandError:  # UpstreamError included: it is the retryable subclass
        partial.unlink(missing_ok=True)
        raise
    os.replace(partial, target)
