"""The network boundary: one client, one capped read, one failure class.

Every member marks its requests with the shared origin and maps a response
onto the exit contract the same way, so an agent reads one rule rather than
one per skill.
"""

from __future__ import annotations

import ssl
from collections.abc import Callable, Mapping
from pathlib import Path

import certifi
import httpx

from btm_corekit.errors import CommandError, UpstreamError
from btm_corekit.origin import user_agent

HTTP_BAD_REQUEST = 400
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500

CONNECT_TIMEOUT = 30.0


def status_failure(status: int, url: str) -> CommandError:
    """A 5xx or a rate limit may clear on a retry; any other 4xx is the
    request's own problem, and retrying it changes nothing."""
    text = f"HTTP {status} from {url}"
    if status >= HTTP_SERVER_ERROR or status == HTTP_TOO_MANY_REQUESTS:
        return UpstreamError(text)
    return CommandError(text)


def build_client(
    skill: str,
    *,
    read_timeout: float | None = CONNECT_TIMEOUT,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """A pooled client for one skill. `read_timeout=None` suits a large
    download, where a stalled peer is caught by the connect and write bounds
    instead. certifi supplies the roots, so an image with none still works.
    """
    return httpx.Client(
        http2=True,
        follow_redirects=True,
        timeout=httpx.Timeout(
            read_timeout,
            connect=CONNECT_TIMEOUT,
            write=CONNECT_TIMEOUT,
            pool=CONNECT_TIMEOUT,
        ),
        verify=ssl.create_default_context(cafile=certifi.where()),
        headers={"User-Agent": user_agent(skill)},
        transport=transport,
    )


def stream(
    client: httpx.Client,
    url: str,
    sink: Callable[[bytes], object],
    cap: int,
    params: Mapping[str, str] | None = None,
) -> None:
    """Feed the body to `sink` in chunks, refusing past `cap`.

    The cap is what keeps a slow drip from growing without bound inside the
    per-read timeout. Exceeding it is the caller's limit, not the server's
    fault, so it asks for a bigger cap rather than a retry.
    """
    try:
        with client.stream("GET", url, params=params) as response:
            if response.status_code >= HTTP_BAD_REQUEST:
                raise status_failure(response.status_code, str(response.url))
            written = 0
            for chunk in response.iter_bytes():
                written += len(chunk)
                if written > cap:
                    raise CommandError(
                        f"{url} sends more than {cap} bytes; raise the cap"
                    )
                sink(chunk)
    except httpx.HTTPError as err:
        raise UpstreamError(f"cannot reach {url}: {err}") from err


def get_bytes(
    client: httpx.Client,
    url: str,
    cap: int,
    params: Mapping[str, str] | None = None,
) -> bytes:
    """The whole body, under the cap."""
    chunks: list[bytes] = []
    stream(client, url, chunks.append, cap, params)
    return b"".join(chunks)


def download(client: httpx.Client, url: str, target: Path, cap: int) -> None:
    """Stream to a sibling partial, then rename, so a target file is either
    absent or complete. The caller owns what a partial left behind means."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{target.name}.partial")
    try:
        with partial.open("wb") as out:
            stream(client, url, out.write, cap)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(target)
