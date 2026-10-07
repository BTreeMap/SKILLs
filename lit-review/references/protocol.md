# Protocol: question, review type, criteria

Fix the review's scope before any search runs. The phase takes the user's
request and leaves a session whose `protocol.json` holds the question, the
level, and non-empty inclusion and exclusion criteria.

## Clarify first

Confirm four inputs. Ask only the ones whose answer would change the output,
at most three; if the user says proceed, choose defaults and state the
assumptions at the top of the report.

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

Then run `init` with the question and the level.

## Criteria

Fill `criteria.include` and `criteria.exclude` in `protocol.json` with
concrete, checkable statements. The script refuses to search until both
lists are non-empty.

- Inclusion: topic relevance stated narrowly, year window, source types,
  methodology kinds accepted.
- Exclusion: off-topic neighbors likely to pollute results, languages not
  read, publication forms not accepted (abstracts only, editorials).
- A criterion an agent cannot check against a record ("high quality") does
  not belong here; extract appraises quality.

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

When the user names papers they already trust, record them first: search for
each by title or DOI so it enters the corpus as a record, then mark it
included with reason "user-supplied seed". Seeds anchor snowballing and
leave the framing untested.
