"""The checker's laws, on the miniature lexicon: what each decidable rule
finds, what stays a signal, and how the splitter cuts."""

from __future__ import annotations

import pytest

from btm_asd_ste100.check import (
    WORD,
    Mode,
    allow_terms,
    check,
    limits,
    paragraphs,
    sentences,
    vocabulary,
    word_count,
)
from btm_asd_ste100.records import Lexicon, Rules
from btm_corekit import CommandError, parse_model


@pytest.fixture
def run(lexicon_doc, rules_doc):
    vocab = vocabulary(parse_model(Lexicon, lexicon_doc, "lexicon"))
    rules = parse_model(Rules, rules_doc, "rules")

    def go(text: str, mode: Mode = Mode.PROCEDURE, allow: str | None = None) -> dict:
        return check(text, mode, vocab, limits(rules, mode), allow_terms(allow))

    return go


def kinds(report: dict, key: str = "findings") -> list[str]:
    return [f["kind"] for f in report[key]]


class TestSplitter:
    @pytest.mark.parametrize(
        "text",
        [
            "Remove the test. Install the test.",
            "Install it 6.5 mm from the edge. Then remove it.",
            "Do these steps:\n- Remove the test\n- Install the test",
            "See e.g. the test. (2) Remove it!",
        ],
    )
    def test_no_word_is_lost_or_reordered(self, text):
        pieces = [s for p in paragraphs(text) for s in sentences(p)]
        assert [w for s in pieces for w in WORD.findall(s)] == WORD.findall(text)

    def test_a_decimal_does_not_end_a_sentence(self):
        assert len(sentences("Install it 6.5 mm from the edge.")) == 1

    def test_a_lowercase_word_after_a_period_does_not_start_one(self):
        assert len(sentences("Turn it 0.1 in. until it stops.")) == 1

    def test_a_colon_before_a_list_and_each_item_are_sentences(self):
        """Rule 8.4: the colon acts as a period; each item is a sentence."""
        got = sentences("Do these steps:\n- Remove the test\n- Install the test")
        assert len(got) == 3

    def test_a_blank_line_separates_paragraphs(self):
        assert len(paragraphs("Remove it.\n\n  \nInstall it.")) == 2


class TestWordCount:
    @pytest.mark.parametrize(
        ("sentence", "words"),
        [
            ("Remove the safety pin (10).", 5),
            (
                "Make sure that the EMER pushbutton switch is released "
                "(the EMER legend is off).",
                10,
            ),
            ("Clean it with a soap-and-water solution.", 6),
            ("Drain 2 liters and 6 mm of oil.", 6),
            ('Set the switch to "TEST MODE ON".', 5),
        ],
    )
    def test_rule_8_groups_count_as_one_word(self, sentence, words):
        assert word_count(sentence) == words


class TestFindings:
    def test_clean_text_is_ok(self, run):
        report = run("Remove the test. Make sure that the test is done.")
        assert report["ok"] and report["findings"] == []

    def test_a_long_procedural_sentence(self, run):
        report = run("Remove the test and install the test with the test.")
        (f,) = report["findings"]
        assert (f["rule"], f["words"], f["limit"]) == ("5.1", 10, 7)

    def test_a_note_takes_the_note_limit(self, run):
        assert run("NOTE: Remove the test and the test with the test.")["ok"]

    def test_description_mode_sets_its_own_limit(self, run):
        text = "Remove the test and install the faster test."
        assert kinds(run(text, Mode.PROCEDURE)) == ["sentence_length"]
        assert run(text, Mode.DESCRIPTION)["ok"]

    def test_the_paragraph_limit_applies_to_description_only(self, run):
        text = "Remove the test. Remove the test. Remove the test."
        assert "paragraph_length" in kinds(run(text, Mode.DESCRIPTION))
        procedure = run(text, Mode.PROCEDURE)
        assert procedure["ok"]
        assert any("6.6" in s for s in procedure["skipped"])

    def test_an_unapproved_headword_carries_its_alternatives(self, run):
        (f,) = run("Ensure the test.")["findings"]
        assert (f["rule"], f["token"], f["alternatives"]) == (
            "1.1",
            "Ensure",
            ["make sure (v)"],
        )

    def test_repeats_of_one_word_share_a_finding(self, run):
        (f,) = run("Remove the pump. Install the pump.")["findings"]
        assert f["sentences"] == [0, 1]

    def test_an_ing_form_names_its_verb(self, run):
        (f,) = run("Do the installing.")["findings"]
        assert (f["rule"], f["verb"]) == ("3.5", "install")

    def test_an_approved_ing_word_passes(self, run):
        assert run("Remove the opening.")["ok"]

    def test_a_contraction_and_a_semicolon(self, run):
        report = run("Don't remove the test; do the test.")
        assert {"contraction", "punctuation"} <= set(kinds(report))

    def test_a_multi_word_approved_term_passes_whole(self, run):
        assert run("Make sure that the test is done.")["ok"]
        assert "sure" in [f["token"] for f in run("Do sure.")["findings"]]


class TestAllowList:
    def test_a_declared_noun_and_its_plural_pass(self, run):
        allow = "# technical nouns\npump\nfuel line\n"
        assert run("Remove the pump. Remove the pumps.", allow=allow)["ok"]
        assert run("Remove the fuel line.", allow=allow)["ok"]

    def test_numbers_units_and_number_words_pass(self, run):
        assert run("Remove 2 mm. Remove two.")["ok"]


class TestSignals:
    def test_signals_never_flip_ok(self, run):
        report = run("The test is installed by a test.", Mode.DESCRIPTION)
        assert report["ok"]
        (s,) = [s for s in report["signals"] if s["kind"] == "passive_candidate"]
        assert s["agent_named"] is True

    def test_an_approved_noun_that_is_an_unapproved_verb(self, run):
        (s,) = run("Test the test.")["signals"]
        assert (s["token"], s["approved_as"], s["not_approved_as"]) == (
            "test",
            ["n"],
            ["v"],
        )
        assert s["sentences"] == [0, 0]

    def test_capitals_in_mixed_text_pass_as_a_label(self, run):
        report = run("Remove the EMER opening.")
        assert report["ok"] and kinds(report, "signals") == ["abbreviation"]

    def test_capitals_in_shouted_text_are_still_checked(self, run):
        assert not run("REMOVE THE EMER TEST.")["ok"]

    def test_a_second_instruction_after_and(self, run):
        report = run("Remove it and install it.")
        assert "second_instruction" in kinds(report, "signals")


class TestLimits:
    def test_a_missing_parameter_is_refused(self, rules_doc):
        rules = parse_model(
            Rules, {**rules_doc, "rules": rules_doc["rules"][1:]}, "rules"
        )
        with pytest.raises(CommandError, match="lacks a parameter"):
            limits(rules, Mode.PROCEDURE)
