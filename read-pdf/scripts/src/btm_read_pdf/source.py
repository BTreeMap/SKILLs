"""Where a PDF comes from: a local path, or a URL materialized through a cache."""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from btm_corekit import CommandError, UpstreamError, user_agent

TIMEOUT_SECONDS = 30
DEFAULT_MAX_BYTES = 200 * 1024 * 1024
HTTP_BAD_REQUEST = 400
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500


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


def cache_dir() -> Path:
    """Regenerable downloads live in temp space, owner-named per convention."""
    return Path(tempfile.gettempdir()) / "btm-read-pdf"


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
            target = cache_dir() / (hashlib.sha256(url.encode()).hexdigest() + ".pdf")
            if target.is_file():
                print(
                    f"note: reusing cached download: {target} (delete it to refetch)",
                    file=sys.stderr,
                )
            else:
                _fetch(url, target, max_bytes, transport)
            return target, url
    raise AssertionError("unreachable: Source is a closed union")


def _status_failure(status: int, url: str) -> CommandError:
    """A 5xx or a rate limit is the server's problem and a retry may clear it;
    a 404 or a 403 is the URL's, and retrying changes nothing. The exit code
    the agent reads follows that split."""
    text = f"HTTP {status} fetching {url}"
    if status >= HTTP_SERVER_ERROR or status == HTTP_TOO_MANY_REQUESTS:
        return UpstreamError(text)
    return CommandError(text)


def _fetch(
    url: str, target: Path, max_bytes: int, transport: httpx.BaseTransport | None
) -> None:
    """Stream to a per-process partial, cap enforced per chunk, sniff the PDF
    magic, rename on success.

    The pid in the partial name keeps concurrent fetches of one URL from
    interleaving; os.replace makes the last completed writer win, and both
    wrote the same URL. The magic check gates the cache: a paywall's HTML
    page must fail here once, never poison the cache and fail in pypdf
    forever.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{target.name}.{os.getpid()}.partial")
    client = httpx.Client(
        follow_redirects=True,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": user_agent("read-pdf")},
        transport=transport,
    )
    try:
        with client, client.stream("GET", url) as response:
            if response.status_code >= HTTP_BAD_REQUEST:
                raise _status_failure(response.status_code, url)
            written = 0
            with open(partial, "wb") as out:
                for chunk in response.iter_bytes():
                    written += len(chunk)
                    if written > max_bytes:
                        raise CommandError(
                            f"download exceeds {max_bytes} bytes; "
                            "pass --max-bytes to raise the cap"
                        )
                    out.write(chunk)
        with open(partial, "rb") as head:
            # The spec tolerates up to 1024 bytes of preamble before %PDF-.
            if b"%PDF-" not in head.read(1024):
                raise CommandError(f"fetched content is not a PDF: {url}")
    except httpx.HTTPError as err:
        partial.unlink(missing_ok=True)
        raise UpstreamError(f"cannot fetch {url}: {err}") from err
    except CommandError:  # UpstreamError included: it is the retryable subclass
        partial.unlink(missing_ok=True)
        raise
    os.replace(partial, target)
