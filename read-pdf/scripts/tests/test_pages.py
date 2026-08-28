"""Laws of the page-selection algebra."""

from __future__ import annotations

import pytest

from btm_read_pdf.pages import parse_page_specification, parse_page_token


class TestParsePageToken:
    def test_single_page_selects_itself(self):
        assert list(parse_page_token(10, "3")) == [3]

    def test_closed_range_is_inclusive_of_both_ends(self):
        assert list(parse_page_token(10, "2-4")) == [2, 3, 4]

    def test_open_ended_range_runs_to_the_last_page(self):
        assert list(parse_page_token(5, "3-")) == [3, 4, 5]

    def test_full_span_is_expressible(self):
        assert list(parse_page_token(3, "1-3")) == [1, 2, 3]

    @pytest.mark.parametrize("token", ["", "abc", "1-2-3", "-2", "1.5", " 1"])
    def test_malformed_tokens_are_rejected(self, token):
        with pytest.raises(ValueError, match="Invalid page selection"):
            parse_page_token(10, token)

    @pytest.mark.parametrize("token", ["0", "11", "4-3", "1-11"])
    def test_out_of_range_selections_are_rejected(self, token):
        with pytest.raises(ValueError, match="outside the document"):
            parse_page_token(10, token)


class TestParsePageSpecification:
    def test_absent_specification_selects_every_page(self):
        assert parse_page_specification(None, 4) == [1, 2, 3, 4]

    def test_comma_list_concatenates_in_written_order(self):
        assert parse_page_specification("3,1", 5) == [3, 1]

    def test_surrounding_whitespace_is_tolerated(self):
        assert parse_page_specification(" 1 , 3 ", 5) == [1, 3]

    def test_overlapping_selections_keep_first_occurrence_only(self):
        assert parse_page_specification("1-3,2-4", 5) == [1, 2, 3, 4]

    def test_mixed_tokens_compose(self):
        assert parse_page_specification("1-3,5,8-", 9) == [1, 2, 3, 5, 8, 9]

    def test_one_page_document_is_fully_selectable(self):
        assert parse_page_specification(None, 1) == [1]

    def test_a_bad_token_rejects_the_whole_specification(self):
        with pytest.raises(ValueError):
            parse_page_specification("1,99", 5)
