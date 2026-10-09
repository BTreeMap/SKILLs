# Verb: write

Write new code functionally from start: domain model first, pure core
second, shell last.

## Pipeline

### 1. Pin the contract

From request, callers-to-be, repository conventions, fix: input and output
domains, error channel (`Option`, `Result`, exception at boundary), effects
performed, expected input sizes, public API surface. State assumptions that
could change design; ask one focused question only if answer would.

### 2. Model the domain

Run kernel's Domain Modeling steps at scale task warrants: full model for
new module, single refined type for small function. Repository already owns
matching domain type: reuse it; never mint parallel one.

### 3. Choose algebra and structures

Pick `map`/`filter`/`fold` vocabulary for each transformation and data
structure for each dominant operation from cost-signal table. State intended
bound before writing body: code's shape follows from bound, not reverse.

### 4. Write pure core, then shell

- Pure core: total functions over domain types, native combinators,
  exhaustive elimination, no I/O, no clock, no randomness.
- Thin shell: one explicit boundary performing effects, honoring loaded
  profile's resource, cancellation, boundedness constraints.
- Apply kernel's Cost Guard as you write, with loaded profile's steps.

### 5. Validate

Write tests alongside code, not after, under kernel's Validation: add empty
and large inputs, effect order, resource cleanup, and property-based tests,
where repository already supports them, for any law relied on (fold
identity/associativity, roundtrips, idempotence). Run new tests.

## Output Contract

Deliver code, then report briefly:

1. Language profile loaded; standard/edition targeted.
2. Domain types introduced or reused; invalid states they exclude.
3. Complexity of dominant operations against expected sizes.
4. Effect boundary and its bounds (concurrency, retries, resources).
5. Validation run; remaining uncertainty.

## Completion Checks

- Domain types existed before function bodies using them.
- Existing repository types and helpers reused over parallel inventions.
- Pure core performs no I/O, clock, or randomness access.
- Stated bounds preceded implementation; code achieves them.
- Tests cover every variant and rejection path, shipped with code.
