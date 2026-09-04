"""The network boundary: what is worth a retry, and what the cap refuses."""

from __future__ import annotations

import httpx
import pytest

from btm_corekit import (
    CommandError,
    UpstreamError,
    download,
    get_bytes,
    status_failure,
    stream,
)


def served(handler) -> httpx.Client:
    """A client answered by a function, so the boundary runs without a network."""
    return httpx.Client(transport=httpx.MockTransport(handler))


def answering(**response) -> httpx.Client:
    return served(lambda request: httpx.Response(**response))


class TestStatusFailure:
    @pytest.mark.parametrize("status", [500, 503, 429])
    def test_a_server_fault_or_a_rate_limit_is_retryable(self, status):
        assert isinstance(status_failure(status, "https://x"), UpstreamError)

    @pytest.mark.parametrize("status", [400, 403, 404])
    def test_a_request_fault_is_not(self, status):
        """Exit 2 told the agent to retry a URL that can never resolve."""
        failure = status_failure(status, "https://x")
        assert isinstance(failure, CommandError)
        assert not isinstance(failure, UpstreamError)


class TestStream:
    def test_a_body_over_the_cap_asks_for_a_bigger_cap(self):
        """The cap is the caller's limit, so a retry would not help."""
        client = answering(status_code=200, content=b"x" * 100)
        with pytest.raises(CommandError, match="raise the cap") as raised:
            get_bytes(client, "https://example.org/big", 10)
        assert not isinstance(raised.value, UpstreamError)

    def test_a_missing_record_does_not_ask_for_a_retry(self):
        client = answering(status_code=404)
        with pytest.raises(CommandError) as raised:
            get_bytes(client, "https://example.org/gone", 100)
        assert not isinstance(raised.value, UpstreamError)

    def test_an_unreachable_host_is_retryable(self):
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route", request=request)

        with pytest.raises(UpstreamError, match="cannot reach"):
            get_bytes(served(refuse), "https://example.org/x", 100)

    def test_the_whole_body_comes_back_under_the_cap(self):
        client = answering(status_code=200, content=b"payload")
        assert get_bytes(client, "https://example.org/x", 100) == b"payload"


class TestDownload:
    def test_the_target_is_absent_or_complete(self, tmp_path):
        target = tmp_path / "out.bin"
        client = answering(status_code=200, content=b"x" * 100)
        with pytest.raises(CommandError):
            download(client, "https://example.org/big", target, 10)
        assert not target.exists()
        assert list(tmp_path.iterdir()) == []

    def test_a_complete_download_lands_at_the_target(self, tmp_path):
        target = tmp_path / "out.bin"
        download(answering(status_code=200, content=b"ok"), "https://x", target, 100)
        assert target.read_bytes() == b"ok"


def test_stream_feeds_the_sink_in_order():
    seen: list[bytes] = []
    stream(answering(status_code=200, content=b"abc"), "https://x", seen.append, 100)
    assert b"".join(seen) == b"abc"
