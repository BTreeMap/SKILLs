# Verb: build

Write new code functionally from the start; the imperative form never exists.
Domain model first, pure core second, shell last.

## Pipeline

### 1. Pin the contract

From the request, callers-to-be, and repository conventions, fix: input and
output domains, error channel (`Option`, `Result`, exception at the boundary),
effects performed, expected input sizes, and the public API surface. State the
assumptions that could change the design; ask one focused question only if an
answer would.

### 2. Model the domain

Run the `design` verb's state/transition discipline at whatever scale the task
warrants - a full model for a new module, a single refined type for a small
function. The kernel's sum/product/smart-constructor laws bind every untrusted
entry. If the repository already owns a matching domain type, reuse it; never
mint a parallel one.

### 3. Choose algebra and structures

Pick the `map`/`filter`/`fold` vocabulary for each transformation and the data
structure for each dominant operation from the kernel's cost-signal table.
State the intended bound before writing the body: the shape of the code
follows from the bound, not the reverse.

### 4. Write pure core, then shell

- Pure core: total functions over the domain types, native combinators,
  exhaustive elimination, no I/O, no clock, no randomness.
- Thin shell: one explicit boundary performing effects, honoring the loaded
  profile's resource, cancellation, and boundedness constraints.
- Apply the loaded profile's cost guard as you write; descend one abstraction
  level where it demands, exactly as in `refactor` step 4.
- Use the newest constructs the repository's configured standard permits when
  they clarify; consult the profile's Modern Surface section.

### 5. Validate

Write tests alongside the code, not after: every sum variant, every
smart-constructor rejection, empty and large inputs, effect order, resource
cleanup. Property-based tests where the repository already supports them, for
any law you relied on (fold identity/associativity, roundtrips, idempotence).
Run the narrowest formatter, typechecker, linter, and the new tests.

## Output Contract

Deliver the code, then report briefly:

1. Language profile loaded and standard/edition targeted.
2. Domain types introduced or reused, and the invalid states they exclude.
3. Complexity of the dominant operations against expected sizes.
4. Effect boundary and its bounds (concurrency, retries, resources).
5. Validation run and remaining uncertainty.

## Completion Checks

<verb-checklist>
  <item>Domain types existed before the function bodies that use them.</item>
  <item>Existing repository types and helpers were reused over parallel inventions.</item>
  <item>The pure core performs no I/O, clock, or randomness access.</item>
  <item>Stated bounds preceded the implementation and the code achieves them.</item>
  <item>Tests cover every variant and rejection path and shipped with the code.</item>
</verb-checklist>
