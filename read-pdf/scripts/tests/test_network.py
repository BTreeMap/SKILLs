"""What a mocked transport structurally cannot reach.

Every other network test in this repository serves bytes from an
`httpx.MockTransport`, which never redirects, never negotiates TLS, and never
decides a content type. These run against a real host and are excluded from
the default suite; opt in with `pytest -m network`.
"""

from __future__ import annotations

import pytest

from btm_corekit import CommandError
from btm_read_pdf.cli import main
from btm_read_pdf.source import RemotePdf, materialize, parse_source

pytestmark = pytest.mark.network

# Redirects cross-host, 308, to a static object; 158,677 bytes of %PDF-1.4.
SAMPLE = "https://s.joefang.org/sample.pdf"
SAMPLE_BYTES = 158_677


@pytest.fixture(autouse=True)
def own_cache(tmp_path, monkeypatch):
    """A per-test download cache. The real one is keyed by URL digest and
    shared across runs, so a warm entry would hide the fetch under test."""
    monkeypatch.setattr("btm_read_pdf.source.cache_dir", lambda: tmp_path / "cache")


class TestRealFetch:
    def test_a_cross_host_redirect_is_followed(self):
        """s.joefang.org answers 308 to another host. `follow_redirects=True`
        is set in the client and nothing until now proved it."""
        path, display = materialize(RemotePdf(SAMPLE))
        assert path.read_bytes()[:5] == b"%PDF-"
        assert display == SAMPLE, "the extraction cites the URL asked for"

    def test_the_whole_object_arrives(self):
        path, _ = materialize(RemotePdf(SAMPLE))
        assert path.stat().st_size == SAMPLE_BYTES

    def test_a_url_argument_parses_as_remote(self):
        assert parse_source(SAMPLE) == RemotePdf(SAMPLE)

    def test_the_cap_stops_a_real_stream(self):
        """The cap is enforced per chunk, so against a real server it has to
        fire mid-download rather than after a content-length check."""
        with pytest.raises(CommandError, match="pass --max-bytes"):
            materialize(RemotePdf(SAMPLE), max_bytes=1024)

    def test_a_capped_download_leaves_no_partial(self, tmp_path):
        with pytest.raises(CommandError):
            materialize(RemotePdf(SAMPLE), max_bytes=1024)
        cache = tmp_path / "cache"
        assert not cache.exists() or list(cache.iterdir()) == []

    def test_the_second_fetch_reuses_the_cache(self, capsys):
        first, _ = materialize(RemotePdf(SAMPLE))
        capsys.readouterr()
        second, _ = materialize(RemotePdf(SAMPLE))
        assert first == second
        assert "cached" in capsys.readouterr().err


class TestEndToEnd:
    def test_a_url_extracts_through_the_command(self, tmp_path, capsys):
        out = tmp_path / "extract.md"
        assert main([SAMPLE, "--output", str(out)]) == 0
        text = out.read_text(encoding="utf-8")
        assert SAMPLE in text, "provenance cites the URL, not the cache path"
        assert "## PDF page 1" in text

    def test_a_missing_remote_object_is_exit_one(self, capsys):
        """A 404 is the URL's problem, so it must not arrive as the retryable
        exit code. Asserting the status too, since a server answering 200 with
        an HTML error page would also exit 1 and hide a broken split."""
        assert main([SAMPLE.replace("sample.pdf", "absent-object.pdf")]) == 1
        assert "HTTP 404 from" in capsys.readouterr().err
