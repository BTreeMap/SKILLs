"""The tolerance boundary: what a foreign body may vary, and what it may not."""

from __future__ import annotations

import httpx
import pytest

from btm_corekit import Upstream, UpstreamError, decode, json_body


class Nested(Upstream):
    name: str | None = None


class Row(Upstream):
    title: str | None = None
    count: int | None = None
    nested: Nested | None = None
    tags: tuple[str, ...] = ()


def answering(payload: bytes) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=payload)
        )
    )


class TestTolerance:
    def test_a_field_the_service_added_is_not_fatal(self):
        assert decode(Row, {"invented_next_year": 1}, "x").title is None

    def test_a_null_reads_as_the_absent_key(self):
        """A service spells "nothing here" both ways and means the same. A
        declared default covers the missing key; without this it would not
        cover the null, and a nested record would fail to validate."""
        row = decode(Row, {"title": None, "nested": None, "tags": None}, "x")
        assert row.title is None
        assert row.nested is None
        assert row.tags == ()

    def test_a_null_inside_a_nested_record_reads_the_same_way(self):
        row = decode(Row, {"nested": {"name": None}}, "x")
        assert row.nested is not None
        assert row.nested.name is None

    def test_a_field_of_the_wrong_kind_names_itself(self):
        """The one case tolerance does not cover: the service changed shape,
        and the fix is a decoder edit, not a retry the caller can make."""
        with pytest.raises(UpstreamError, match="count") as raised:
            decode(Row, {"count": "many"}, "https://example.org/rows")
        assert "https://example.org/rows" in str(raised.value)
        assert "Row" in str(raised.value)


class TestJsonBody:
    def test_a_body_decodes_into_its_record(self):
        client = answering(b'{"title": "T", "tags": ["a"]}')
        row = json_body(Row, client, "https://example.org/x", 10_000)
        assert row.title == "T" and row.tags == ("a",)

    def test_a_non_json_body_names_its_source(self):
        client = answering(b"<html>")
        with pytest.raises(UpstreamError, match="non-JSON"):
            json_body(Row, client, "https://example.org/x", 10_000)
