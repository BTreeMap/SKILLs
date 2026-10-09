# Ponytail Design Verb

Decide what not to build before code exists. Read requirements, trace what
codebase already does, then run ladder over plan itself. Produces a plan;
edits nothing.

## Output

Kill list, then build list, one line per requirement:

- `skip:` speculative need, nothing depends on it today. (YAGNI)
- `covered:` codebase, stdlib, platform, or installed dependency already
  does it. Name the thing.
- `build:` survives; name ladder rung it sits on and minimum shape.

End with shape of the whole: files touched, new files (fewest possible), new
dependencies (target: zero).

**Example: design** (request: Design a notification system: email, SMS,
push, user preferences, retry queues, analytics.)

```text
skip: SMS, push. No sender and no consumer today; add a channel when one exists.
skip: analytics. Count sends in the DB you already have, when someone asks.
covered: retry. The job runner already retries; a queue table duplicates it.
build: email send, one function on the existing mailer. rung 5.
build: per-user opt-out, one boolean column. rung 4: DB constraint, no prefs service.
Whole: 1 migration, ~40 lines in existing files, 0 new deps.
```
