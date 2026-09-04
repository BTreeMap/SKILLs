# Go Cost Model

## Disclosed Constraints

- No TCO. Collection-sized recursion risks stack growth.
- Higher-order callbacks, closures, interface values, and generic abstraction can
  escape or allocate; Go optimizes many direct loops more predictably.
- The language and ecosystem favor explicit control flow, simple structs, and
  visible error handling over generalized FP machinery.
- Functional options mutate a fresh configuration object: a controlled
  construction pattern.

## Preferred FP Shapes

- Keep a pure conceptual pipeline, but compile ordinary collection transforms to
  direct loops with named pure predicate/projector helpers.
- Use explicit `(value, error)` results, concrete value structs, and small total
  transition functions.
- Use functional options for optional construction-time configuration when the
  repository already favors the pattern. Validate before publication.
- Preallocate result slices when a sound upper bound or exact capacity is known.
- Use standard-library helpers when present; otherwise use a direct fold loop
  over any generic HOF framework.

## Domain and Effect Constraints

- Go has no native algebraic data types or exhaustive matching. Use concrete
  structs with unexported fields and validating constructors for invariants.
  Use a small interface with an unexported marker only when variants genuinely
  require a closed protocol; recognize that compiler exhaustiveness is absent.
- Use `(T, bool)` for lookup-style absence and `(T, error)` for expected failure.
  Do not emulate `Option`/`Result` with a generic monad layer.
- Keep zero values useful when possible. When zero is invalid, hide fields and
  force construction through `NewX`/`ParseX`; methods must preserve the
  invariant.
- Pass `context.Context` explicitly as the first parameter to effectful
  operations. Propagate cancellation and deadlines; never store context in a
  domain value.
- Keep dependent `(T, error)` calls sequential and explicit. Run independent
  effects concurrently only when fan-out is bounded, errors are joined
  deliberately, and sibling work observes the shared cancellation context.
- Pair every acquisition with immediate `defer` after a successful open. Check
  close/flush errors when they affect correctness.
- Bound goroutines and channels, define channel ownership/closure, and avoid
  goroutine leaks on early return. Preserve database transaction boundaries and
  idempotency under retries.

## Teaching Example

<teaching-example language="go">
<![CDATA[
package domain

import (
	"errors"
	"strings"
)

type Email struct{ value string }

func ParseEmail(raw string) (Email, error) {
    normalized := strings.ToLower(strings.TrimSpace(raw))
    if !strings.Contains(normalized, "@") {
        return Email{}, errors.New("invalid email")
    }
    return Email{value: normalized}, nil
}

func (e Email) String() string { return e.value }

func LookupEmail(users map[string]Email, id string) (Email, bool) {
    email, ok := users[id]
    return email, ok
}
]]></teaching-example>

Taste: the unexported field and parser create the strongest practical invariant;
`error` signals invalid input and `bool` ordinary absence. Explicit control
flow beats an imported monad vocabulary.

## Cost Guard

1. Replace recursion with iteration.
2. If a closure or interface abstraction escapes on a relevant path, use a named
   function and concrete types.
3. If a `map`/`filter` helper obscures allocation or control flow, retain the
   algebra in pure helpers and use one explicit loop.
4. Confine unavoidable mutation to a fresh local value; publish only a completed
   valid result.
5. Preserve explicit error timing and partial-result contracts.
6. Preserve context propagation, cleanup, goroutine/channel ownership,
   transaction scope, and concurrency bounds.

## Validation Focus

Run formatting, package tests, and static analysis when configured. Use existing
benchmarks and escape analysis for hot paths; otherwise report closure/allocation
risk as unmeasured.
