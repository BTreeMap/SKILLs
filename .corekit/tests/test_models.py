"""The modelling layer: refined primitives, and the bridge that keeps a
pydantic rejection readable as a corrective order."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from btm_corekit import Diagnostic
from btm_corekit.models import (
    ArxivId,
    Doi,
    Keyword,
    Model,
    NonEmpty,
    Slug,
    diagnostics,
    dump,
    refuse,
    where_of,
)


class TestRefinedPrimitives:
    @pytest.mark.parametrize(
        ("kind", "raw", "parsed"),
        [
            (Doi, "  10.1175/JAS-D-18.1 ", "10.1175/jas-d-18.1"),
            (ArxivId, " 2405.08387", "2405.08387"),
            (Keyword, " Rent ", "rent"),
            (Slug, " Rent-Length ", "rent-length"),
            (NonEmpty, "  x  ", "x"),
        ],
    )
    def test_normalization_happens_in_the_type(self, kind, raw, parsed):
        assert TypeAdapter(kind).validate_python(raw) == parsed

    @pytest.mark.parametrize(
        ("kind", "raw"),
        [
            (Doi, "not-a-doi"),
            (Doi, "10.1/x"),  # registrant prefix is 4 to 9 digits
            (ArxivId, "2405.8"),
            (Keyword, "rent-length"),  # a keyword carries no separator
            (Slug, "Rent Length"),
            (NonEmpty, "   "),
        ],
    )
    def test_a_value_outside_the_refinement_is_refused(self, kind, raw):
        with pytest.raises(ValidationError):
            TypeAdapter(kind).validate_python(raw)


class TestModelBase:
    class Record(Model):
        name: NonEmpty

    def test_records_are_frozen(self):
        record = self.Record(name="x")
        with pytest.raises(ValidationError):
            record.name = "y"

    def test_an_unknown_field_is_refused_rather_than_dropped(self):
        with pytest.raises(ValidationError, match="Extra inputs"):
            self.Record(name="x", invented=1)

    def test_dump_omits_absent_fields(self):
        assert dump(self.Record(name="x")) == {"name": "x"}


class TestLocations:
    @pytest.mark.parametrize(
        ("loc", "where"),
        [
            ((), "$"),
            (("objections", 0, "anchors", 1), "objections[0].anchors[1]"),
            (("claims",), "claims"),
            (("leaves", 2), "leaves[2]"),
        ],
    )
    def test_a_location_reads_as_the_agent_already_reads_one(self, loc, where):
        assert where_of(loc) == where


class TestCorrectiveOrders:
    def test_every_cross_field_problem_arrives_in_one_verdict(self):
        """The property the gate exists for: a rejection costs one edit."""
        problems = [
            Diagnostic("objections[0].anchors", "quote the paper verbatim", "page 3"),
            Diagnostic("objections[0].prior", "drop prior keys here"),
        ]
        with pytest.raises(ValidationError) as caught:
            refuse("Objection", problems)
        assert diagnostics(caught.value) == problems

    def test_the_bridge_round_trips_locations_and_hints(self):
        original = [
            Diagnostic("$", "add at least one entry"),
            Diagnostic("a[1].b", "f"),
        ]
        with pytest.raises(ValidationError) as caught:
            refuse("M", original)
        assert diagnostics(caught.value) == original

    def test_native_field_errors_translate_too(self):
        class Record(Model):
            name: NonEmpty
            doi: Doi

        with pytest.raises(ValidationError) as caught:
            Record(name="", doi="nope")
        problems = diagnostics(caught.value)
        assert {problem.where for problem in problems} == {"name", "doi"}
        assert all(problem.fix for problem in problems)
