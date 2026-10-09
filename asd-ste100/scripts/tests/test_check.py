"""The checker's laws, on the miniature lexicon: what each decidable rule
finds, what stays a signal, and how the splitter cuts."""

from __future__ import annotations

import pytest

from btm_asd_ste100.check import (
    WORD,
    Mode,
    accept_terms,
    check,
    limits,
    paragraphs,
    sentences,
    vocabulary,
    word_count,
)
from btm_asd_ste100.layout import Cut, Format
from btm_asd_ste100.records import Lexicon, Rules
from btm_corekit import CommandError, parse_model


@pytest.fixture
def run(lexicon_doc, rules_doc):
    vocab = vocabulary(parse_model(Lexicon, lexicon_doc, "lexicon"))
    rules = parse_model(Rules, rules_doc, "rules")

    def go(
        text: str,
        mode: Mode = Mode.PROCEDURE,
        accept: str | None = None,
        how: Cut = Cut(),  # noqa: B008 - frozen, so one shared default is safe
    ) -> dict:
        return check(text, vocab, limits(rules, mode), accept_terms(accept), how)

    return go


def types(report: dict, key: str = "findings") -> list[str]:
    return [f["type"] for f in report[key]]


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

    @pytest.mark.parametrize("close", ["”", '"', ")", "'"])
    def test_a_closing_mark_after_the_period_ends_a_sentence(self, close):
        """The spec writes 'SHOWS: “NO GO.” IF THERE IS': two sentences."""
        opening = {"”": "“", ")": "("}.get(close, close)
        text = f"The screen shows {opening}stop.{close} Remove the test."
        assert len(sentences(text)) == 2

    def test_a_decimal_does_not_end_a_sentence(self):
        assert len(sentences("Install it 6.5 mm from the edge.")) == 1

    def test_a_lowercase_word_after_a_period_does_not_start_one(self):
        assert len(sentences("Turn it 0.1 in. until it stops.")) == 1

    def test_a_colon_before_a_list_and_each_item_are_sentences(self):
        """Rule 8.4: the colon acts as a period; each item is a sentence."""
        got = sentences("Do these steps:\n- Remove the test\n- Install the test")
        assert len(got) == 3

    def test_a_code_span_after_a_period_starts_a_sentence(self, run):
        assert run("Remove the test. `x` is done.")["counts"]["sentences"] == 2

    def test_a_colon_at_a_wrapped_line_end_ends_nothing(self):
        assert len(sentences("Use the form (fast:\nfaster) here.")) == 1

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
            ("Run `$R check --text:file draft.txt` again.", 3),
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
        assert types(run(text, Mode.PROCEDURE)) == ["sentence_length"]
        assert run(text, Mode.DESCRIPTION)["ok"]

    def test_the_paragraph_limit_applies_to_description_only(self, run):
        text = "Remove the test. Remove the test. Remove the test."
        assert "paragraph_length" in types(run(text, Mode.DESCRIPTION))
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

    def test_an_ing_word_outside_the_approved_few(self, run):
        (f,) = run("Do the installing.")["findings"]
        assert (f["rule"], f["type"]) == ("3.5", "ing_form")

    def test_an_approved_ing_word_passes(self, run):
        assert run("Remove the opening.")["ok"]

    def test_a_contraction_and_a_semicolon(self, run):
        report = run("Don't remove the test; do the test.")
        assert {"contraction", "punctuation"} <= set(types(report))

    def test_a_code_span_is_not_checked(self, run):
        assert run("Remove the `frobnicate --utilize` test.")["ok"]

    def test_quoted_text_is_a_technical_noun_and_a_signal(self, run):
        report = run('Do not remove the "utilize" test.')
        assert report["ok"]
        (s,) = [s for s in report["signals"] if s["type"] == "quotation"]
        assert (s["text"], s["lines"]) == ('"utilize"', [1])

    def test_an_inflected_unapproved_word_carries_its_alternatives(self, run):
        (f,) = run("Remove the ensured test.")["findings"]
        assert (f["token"], f["headword"], f["alternatives"]) == (
            "ensured",
            "ensure",
            ["make sure (v)"],
        )
        assert "next" not in f

    def test_an_unapproved_ing_headword_is_reported_under_1_1(self, run):
        (f,) = run("Remove the finding.")["findings"]
        assert (f["rule"], f["type"], f["alternatives"]) == (
            "1.1",
            "not_approved",
            ["test (n)"],
        )

    def test_a_headword_with_no_alternative_carries_its_help(self, run):
        (f,) = run("Remove the test whose test.")["findings"]
        assert (f["alternatives"], f["help"]) == ([], "Use a different construction.")
        assert "next" not in f

    def test_alternatives_are_listed_once(self, run):
        (f,) = run("Return the test.")["findings"]
        assert f["alternatives"] == ["do (v)"]

    def test_each_finding_names_its_source_line(self, run):
        report = run("Remove the test.\n\nRemove the pump.\nInstall the pump.")
        (f,) = report["findings"]
        assert (f["sentences"], f["lines"]) == ([1, 2], [3, 4])

    def test_the_summary_counts_by_type_and_names_the_words(self, run):
        summary = run("Ensure the pump.")["summary"]
        assert summary["findings"] == {"not_approved": 2}
        assert summary["words"] == ["Ensure", "pump"]

    def test_a_multi_word_approved_term_passes_whole(self, run):
        assert run("Make sure that the test is done.")["ok"]
        assert "sure" in [f["token"] for f in run("Do sure.")["findings"]]


class TestPhrases:
    """Rule 1.1 for unapproved headwords of more than one word."""

    def test_an_inflected_phrasal_verb_names_its_headword(self, run):
        (f,) = run("Then the test turned off.", accept="then")["findings"]
        assert (f["token"], f["headword"]) == ("turned off", "turn off")

    def test_a_phrasal_verb_with_a_word_that_fails_alone_is_a_finding(self, run):
        """AWAY is approved only in AWAY FROM, so 'get away' stays a finding."""
        (f,) = run("Get away the test.")["findings"]
        assert (f["type"], f["token"]) == ("not_approved", "Get away")

    def test_the_words_of_the_phrase_alone_pass(self, run):
        assert run("Turn the test. Remove the test off.")["ok"]

    def test_a_qualified_entry_is_found_as_its_phrase(self, run):
        """few (a few) is a phrase entry; the bare word keeps its own."""
        report = run("Remove a few tests. Remove few tests.")
        got = {f["token"]: f["alternatives"] for f in report["findings"]}
        assert got == {"a few": ["do (v)"], "few": ["small number"]}

    def test_a_qualifier_with_a_form_of_the_headword_is_the_phrase(self, run):
        """long (no longer): the qualifier holds "longer", not "long"."""
        (f,) = run("The test is no longer fast.")["findings"]
        assert (f["token"], f["alternatives"]) == ("no longer", ["not (adv)"])

    def test_a_phrase_that_overlaps_an_approved_one_is_found(self, run):
        """'Get away from': get away starts first; away from is approved."""
        report = run("Get away from the test.")
        assert [f["token"] for f in report["findings"]] == ["Get away"]

    def test_an_unapproved_hyphenated_headword_is_found(self, run):
        """Every part is declared, but the whole is a headword."""
        (f,) = run("Hand-tighten the test.", accept="hand\ntighten")["findings"]
        assert (f["token"], f["alternatives"]) == ("Hand-tighten", ["install (v)"])


class TestAcceptList:
    def test_a_declared_noun_and_its_plural_pass(self, run):
        accept = "# technical nouns\npump\nfuel line\n"
        assert run("Remove the pump. Remove the pumps.", accept=accept)["ok"]
        assert run("Remove the fuel line.", accept=accept)["ok"]

    def test_a_declared_noun_passes_as_a_possessive(self, run):
        assert run("Remove the pump's test.", accept="pump\n")["ok"]

    def test_a_word_of_a_multi_word_term_does_not_pass_alone(self, run):
        accept = "fuel line\n"
        assert run("Remove the fuel lines.", accept=accept)["ok"]
        (f,) = run("Remove the line.", accept=accept)["findings"]
        assert f["token"] == "line"

    def test_numbers_units_and_number_words_pass(self, run):
        assert run("Remove 2 mm. Remove two.")["ok"]


class TestSignals:
    def test_signals_never_flip_ok(self, run):
        report = run("The test is installed by a test.", Mode.DESCRIPTION)
        assert report["ok"]
        (s,) = [s for s in report["signals"] if s["type"] == "passive_candidate"]
        assert s["agent_named"] is True

    def test_an_approved_noun_that_is_an_unapproved_verb(self, run):
        (s,) = run("Test the test.")["signals"]
        assert (s["token"], s["approved_as"], s["not_approved_as"]) == (
            "test",
            ["n"],
            ["v"],
        )
        assert s["sentences"] == [0]  # once per sentence, however often
        assert s["context"] == ["Test", "the test"]  # the word before is evidence

    def test_a_regular_form_of_an_unapproved_verb_is_signaled(self, run):
        """'tests' is the approved plural of TEST (n) and the -s form of
        test (v); find links it to the verb, so check signals it."""
        (s,) = run("The opening tests.")["signals"]
        assert (s["type"], s["token"], s["not_approved_as"]) == (
            "part_of_speech",
            "tests",
            ["v"],
        )

    def test_a_number_word_that_is_an_unapproved_verb_is_signaled(self, run):
        """ZERO is a technical noun as a number (rule 1.5) and zero (v) is
        not approved: 'Zero the opening.' passes but carries the signal."""
        report = run("Zero the opening. Set the opening to zero.", accept="set\nto")
        assert report["ok"]
        (s,) = report["signals"]
        assert (s["type"], s["token"], s["approved_as"], s["not_approved_as"]) == (
            "part_of_speech",
            "zero",
            ["tn"],
            ["v"],
        )
        assert (s["alternatives"], s["context"]) == (["zero (TN)"], ["Zero", "to zero"])

    def test_a_number_word_that_is_no_headword_is_not_signaled(self, run):
        assert run("Remove two.")["signals"] == []

    def test_capitals_in_mixed_text_pass_as_a_label(self, run):
        report = run("Remove the EMER opening.")
        assert report["ok"] and types(report, "signals") == ["abbreviation"]

    def test_one_abbreviation_signal_per_label(self, run):
        (s,) = run("Remove the EMER opening. Install the EMER opening.")["signals"]
        assert (s["type"], s["sentences"]) == ("abbreviation", [0, 1])

    def test_capitals_in_shouted_text_are_still_checked(self, run):
        assert not run("REMOVE THE EMER TEST.")["ok"]

    def test_a_shouted_sentence_in_mixed_text_is_still_checked(self, run):
        """Capitals decide per sentence: one warning in capitals among
        sentence-case text has no labels."""
        report = run("Remove the test. Remove the opening. REMOVE THE EMER.")
        assert [f["token"] for f in report["findings"]] == ["EMER"]

    def test_a_label_in_a_mixed_sentence_passes_in_shouted_text(self, run):
        report = run("REMOVE THE OPENING. INSTALL THE OPENING. Remove the EMER.")
        assert report["ok"] and types(report, "signals") == ["abbreviation"]

    def test_a_second_instruction_after_and(self, run):
        report = run("Remove it and install it.")
        assert "second_instruction" in types(report, "signals")


class TestLimits:
    def test_a_missing_parameter_is_refused(self, rules_doc):
        rules = parse_model(
            Rules, {**rules_doc, "rules": rules_doc["rules"][1:]}, "rules"
        )
        with pytest.raises(CommandError, match="lacks a parameter"):
            limits(rules, Mode.PROCEDURE)


MARKDOWN = """---
name: x
---

# Remove

Remove the test. Install
the test.

* Remove the pump.
* Install the test.

| Test | Do |
| --- | --- |
| `write` | Remove the test. Install the test. |

```
utilize the frobnicator
```

<commands for="surface">
$R utilize --ensure
</commands>

<procedure>
  <step>Remove the [test](https://example.org/utilize).</step>
</procedure>

## Install

Install the pump.
"""


class TestMarkdown:
    def report(self, run, section: str | None = None) -> dict:
        return run(MARKDOWN, Mode.DESCRIPTION, how=Cut(Format.MARKDOWN, section))

    def test_code_front_matter_and_payloads_are_not_prose(self, run):
        words = self.report(run)["summary"]["words"]
        assert words == ["pump"]

    def test_blocks_are_headings_items_rows_and_tag_lines(self, run):
        report = self.report(run)
        assert report["counts"] == {"paragraphs": 9, "sentences": 12, "words": 28}
        (f,) = report["findings"]
        assert f["lines"] == [10, 31]

    def test_a_table_cell_is_a_sentence(self, run):
        cell = run("| Remove the test | Install the test |", how=Cut(Format.MARKDOWN))
        assert cell["counts"]["sentences"] == 2

    def test_a_section_runs_to_the_next_heading(self, run):
        report = self.report(run, "install")
        assert report["counts"]["sentences"] == 2 and report["section"] == "install"
        lead = self.report(run, "Remove")  # a level-1 heading stops at a level 2
        assert lead["counts"]["sentences"] == 10

    def test_a_section_title_may_hold_code(self, run):
        page = "# The `help` card\n\nRemove the pump.\n"
        report = run(page, how=Cut(Format.MARKDOWN, "The `help` card"))
        assert report["summary"]["words"] == ["card", "pump"]

    def test_an_unknown_section_names_the_headings(self, run):
        with pytest.raises(CommandError, match="headings: Remove, Install"):
            self.report(run, "Fix")

    def test_a_section_needs_markdown(self, run):
        with pytest.raises(CommandError, match="--format markdown"):
            run("Remove it.", how=Cut(section="Remove"))
