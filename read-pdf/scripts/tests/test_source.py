"""Source algebra: parsing, materialization, cache reuse, and the size cap."""

from __future__ import annotations

import httpx
import pytest

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
        with pytest.raises(ValueError, match="PDF file not found"):
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
        with pytest.raises(ValueError, match="HTTP 404 fetching"):
            materialize(
                RemotePdf("https://x.org/gone.pdf"),
                transport=transport_serving(b"", status=404),
            )

    def test_the_size_cap_rejects_and_leaves_no_partial(self, tmp_path):
        with pytest.raises(ValueError, match="exceeds 4 bytes"):
            materialize(
                RemotePdf("https://x.org/big.pdf"),
                max_bytes=4,
                transport=transport_serving(PDF_BYTES),
            )
        cache = tmp_path / "cache"
        assert not cache.exists() or list(cache.iterdir()) == []

    def test_non_pdf_content_is_rejected_and_never_cached(self, tmp_path):
        with pytest.raises(ValueError, match="not a PDF"):
            materialize(
                RemotePdf("https://x.org/paywall"),
                transport=transport_serving(b"<html>sign in to view</html>"),
            )
        cache = tmp_path / "cache"
        assert not cache.exists() or list(cache.iterdir()) == []
