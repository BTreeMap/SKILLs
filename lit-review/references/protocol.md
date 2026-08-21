# Protocol: Question, Review Type, Criteria

Everything the review will and will not cover is fixed here, before any
search runs.

## Clarify first

Confirm four inputs. Ask only the ones whose answer would change the output,
at most three; if the user says to just proceed, choose defaults and state
the assumptions at the top of the report.

1. **Research question.** Specific and answerable. "How do X and Y compare
   under condition Z" beats "X and Y". For empirical fields the PICO frame
   helps: population or problem, intervention or phenomenon, comparator,
   outcome. For computing and theory a plain comparative or descriptive
   question is fine.
2. **Review type.** Selects the default level; the user's level word wins.

   | Type | Goal | Default level |
   | --- | --- | --- |
   | Narrative | Orient in a topic, background section | lite |
   | Scoping | Map a field: themes, venues, gaps | full |
   | Systematic | Answer one question from all qualifying evidence | ultra |

3. **Bounds.** Year window, language, geographic or domain scope.
4. **Accepted source types.** Peer-reviewed only, or also preprints,
   conference papers, gray literature. Preprints are normal in fast fields;
   the report labels them.

## Criteria

Write inclusion and exclusion criteria into `protocol.json` as concrete,
checkable statements. The script refuses to search until both lists are
non-empty.

- Inclusion: topic relevance stated narrowly, year window, source types,
  methodology kinds accepted.
- Exclusion: off-topic neighbors likely to pollute results, languages not
  read, publication forms not accepted (abstracts only, editorials).
- A criterion an agent cannot check against a record ("high quality") does
  not belong here; quality is appraised during extract, not screened by
  slogan.

<criteria_example>
"criteria": {
  "include": [
    "evaluates retrieval-augmented generation for factual accuracy",
    "empirical results on at least one public benchmark",
    "published or preprinted 2021 or later"
  ],
  "exclude": [
    "retrieval systems without a generation component",
    "position papers without experiments",
    "not available in English"
  ]
}
</criteria_example>

## Amendments

Changing criteria after searches ran is allowed and visible, never silent.
Append to `amendments` in `protocol.json`: date, what changed, why. The
script flags hash drift in `status`; an unexplained drift is an error to
repair. Papers already screened under the old criteria are re-screened when
the change could flip their decision.

## Seed papers

When the user names papers they already trust, record them first: search for
each by title or DOI so it enters the corpus as a record, then mark it
included with reason "user-supplied seed". Seeds are snowball anchors, not
proof of the question's framing.
