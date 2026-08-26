# Ponytail Design Verb

Plan before code exists - by deciding what not to build. Read the
requirements, trace what the codebase already does, then run the ladder
over the plan itself. Produces a plan; edits nothing.

## Output

The kill list, then the build list. One line per requirement:

- `skip:` speculative need, nothing depends on it today. (YAGNI)
- `covered:` the codebase, stdlib, platform, or an installed dependency
  already does it. Name the thing.
- `build:` survives; name the ladder rung it sits on and the minimum shape.

End with the shape of the whole: files touched, new files (fewest
possible), new dependencies (target: zero).

<design_example request="Design a notification system: email, SMS, push, user preferences, retry queues, analytics.">
skip: SMS, push. No sender and no consumer today; add a channel when one exists.
skip: analytics. Count sends in the DB you already have, when someone asks.
covered: retry. The job runner already retries; a queue table duplicates it.
build: email send, one function on the existing mailer. rung 5.
build: per-user opt-out, one boolean column. rung 4: DB constraint, no prefs service.
Whole: 1 migration, ~40 lines in existing files, 0 new deps.
</design_example>

## Boundaries

Challenge scope, never correctness. Domain modeling and typing the
states route to `/pl-theorist design`.
