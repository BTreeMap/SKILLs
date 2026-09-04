"""Source algebra: parsing, materialization, cache reuse, and the size cap."""

from __future__ import annotations

import httpx
import pytest

from btm_corekit import CommandError, UpstreamError
from btm_read_pdf.source import LocalPdf, RemotePdf, materialize, parse_source

PDF_BYTES = b"%PDF-1.4 tiny"


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("btm_read_pdf.source.cache_dir", lambda: tmp_path / "cache")


def transport_serving(content: bytes, status: int = 200, calls: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url)
        return httpx.Response(status, content=content)

    return httpx.MockTransport(handler)


class TestParseSource:
    def test_an_http_prefix_parses_as_remote(self):
        assert parse_source("https://x.org/a.pdf") == RemotePdf("https://x.org/a.pdf")
        assert parse_source("http://x.org/a.pdf") == RemotePdf("http://x.org/a.pdf")

    def test_an_existing_file_parses_as_local(self, tmp_path):
        path = tmp_path / "a.pdf"
        path.write_bytes(PDF_BYTES)
        assert parse_source(str(path)) == LocalPdf(path)

    def test_a_missing_file_is_rejected(self, tmp_path):
        with pytest.raises(CommandError, match="PDF file not found"):
            parse_source(str(tmp_path / "gone.pdf"))


class TestMaterialize:
    def test_a_local_source_is_identity(self, tmp_path):
        path = tmp_path / "a.pdf"
        path.write_bytes(PDF_BYTES)
        assert materialize(LocalPdf(path)) == (path, "a.pdf")

    def test_a_remote_source_downloads_and_displays_its_url(self):
        url = "https://x.org/a.pdf"
        path, name = materialize(RemotePdf(url), transport=transport_serving(PDF_BYTES))
        assert name == url
        assert path.read_bytes() == PDF_BYTES
        assert [p.name for p in path.parent.iterdir()] == [path.name]

    def test_a_second_materialize_reuses_the_cache(self, capsys):
        url = "https://x.org/a.pdf"
        calls: list = []
        transport = transport_serving(PDF_BYTES, calls=calls)
        first, _ = materialize(RemotePdf(url), transport=transport)
        second, _ = materialize(RemotePdf(url), transport=transport)
        assert first == second
        assert len(calls) == 1
        assert "cached" in capsys.readouterr().err

    def test_an_http_error_is_rejected_cleanly(self):
        with pytest.raises(CommandError, match="HTTP 404 from"):
            materialize(
                RemotePdf("https://x.org/gone.pdf"),
                transport=transport_serving(b"", status=404),
            )

    @pytest.mark.parametrize("status", [400, 403, 404, 410])
    def test_a_client_error_is_not_retryable(self, status):
        """A 404 is the URL's problem; retrying it changes nothing, so it must
        not arrive as the exception that tells an agent to try again."""
        with pytest.raises(CommandError) as raised:
            materialize(
                RemotePdf(f"https://x.org/{status}.pdf"),
                transport=transport_serving(b"", status=status),
            )
        assert not isinstance(raised.value, UpstreamError)

    @pytest.mark.parametrize("status", [429, 500, 502, 503])
    def test_a_server_error_or_rate_limit_is_retryable(self, status):
        with pytest.raises(UpstreamError, match=f"HTTP {status} from"):
            materialize(
                RemotePdf(f"https://x.org/{status}.pdf"),
                transport=transport_serving(b"", status=status),
            )

    def test_a_transport_failure_is_retryable(self):
        def refuse(request):
            raise httpx.ConnectError("connection refused")

        with pytest.raises(UpstreamError, match="cannot reach"):
            materialize(
                RemotePdf("https://x.org/down.pdf"),
                transport=httpx.MockTransport(refuse),
            )

    def test_the_size_cap_rejects_and_leaves_no_partial(self, tmp_path):
        with pytest.raises(CommandError, match="more than 4 bytes"):
            materialize(
                RemotePdf("https://x.org/big.pdf"),
                max_bytes=4,
                transport=transport_serving(PDF_BYTES),
            )
        cache = tmp_path / "cache"
        assert not cache.exists() or list(cache.iterdir()) == []

    def test_non_pdf_content_is_rejected_and_never_cached(self, tmp_path):
        with pytest.raises(CommandError, match="not a PDF"):
            materialize(
                RemotePdf("https://x.org/paywall"),
                transport=transport_serving(b"<html>sign in to view</html>"),
            )
        cache = tmp_path / "cache"
        assert not cache.exists() or list(cache.iterdir()) == []
