# Protocol: question, review type, criteria

Fix review's scope before any search runs. Phase takes user's request,
leaves session whose `protocol.json` holds question, level, non-empty
inclusion and exclusion criteria.

## Clarify first

Confirm four inputs. Ask only ones whose answer would change output, at most
three; user says proceed: choose defaults, state assumptions at top of
report.

1. **Research question.** Specific and answerable. "How do X and Y compare
   under condition Z" beats "X and Y". Empirical fields: PICO frame helps:
   population or problem, intervention or phenomenon, comparator, outcome.
   Computing and theory: plain comparative or descriptive question fine.
2. **Review type.** Selects default level; user's level word wins.

   | Type | Goal | Default level |
   | --- | --- | --- |
   | Narrative | Orient in topic, background section | basic |
   | Scoping | Map field: themes, venues, gaps | full |
   | Systematic | Answer one question from all qualifying evidence | maximum |

3. **Bounds.** Year window, language, geographic or domain scope.
4. **Accepted source types.** Peer-reviewed only, or also preprints,
   conference papers, gray literature. Preprints normal in fast fields;
   report labels them.

Then run `start` with question and level.

## Criteria

Fill `criteria.include` and `criteria.exclude` in `protocol.json` with
concrete, checkable statements. Script refuses to search until both lists
non-empty.

- Inclusion: topic relevance stated narrowly, year window, source types,
  methodology kinds accepted.
- Exclusion: off-topic neighbors likely to pollute results, languages not
  read, publication forms not accepted (abstracts only, editorials).
- Criterion agent cannot check against record ("high quality") does not
  belong here; extract appraises quality.

<example for="criteria">
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
</example>

## Seed papers

User names papers they already trust: record them first. `find` each by
title or DOI so it enters corpus as record, then mark included with reason
"user-supplied seed". Seeds anchor snowballing, leave framing untested.
