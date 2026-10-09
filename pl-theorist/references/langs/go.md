# Go Profile

## Cost Model

- No TCO. Collection-sized recursion risks stack growth.
- Higher-order callbacks, closures, interface values, generic abstraction
  can escape or allocate; Go optimizes many direct loops more predictably.
- Language and ecosystem favor explicit control flow, simple structs,
  visible error handling over generalized FP machinery.

## Domain Shapes

- Go has no native algebraic data types or exhaustive matching. Concrete
  structs with unexported fields and validating constructors for invariants.
  Small interface with unexported marker only when variants require closed
  protocol; compiler exhaustiveness is absent.
- Keep zero values useful when possible. Zero invalid: hide fields, force
  construction through `NewX`/`ParseX`; methods must preserve invariant.
- `(T, bool)` for lookup-style absence, `(T, error)` for expected failure.
  Do not emulate `Option`/`Result` with generic monad layer.
- Functional options for optional construction-time configuration when
  repository already favors pattern; they mutate fresh configuration object,
  controlled construction pattern. Validate before publication.
- Keep pure conceptual pipeline, but compile ordinary collection transforms
  to direct loops with named pure predicate/projector helpers and small
  total transition functions. Standard-library helpers when present;
  otherwise direct fold loop over any generic HOF framework.
- Preallocate result slices when sound upper bound or exact capacity known.

## Effects

- Pass `context.Context` explicitly as first parameter to effectful
  operations. Propagate cancellation and deadlines; never store context in
  domain value.
- Keep dependent `(T, error)` calls sequential and explicit. Run independent
  effects concurrently only when fan-out bounded, errors joined
  deliberately, sibling work observes shared cancellation context.
- Pair every acquisition with immediate `defer` after successful open. Check
  close/flush errors when they affect correctness.
- Bound goroutines and channels, define channel ownership/closure, avoid
  goroutine leaks on early return.

## Teaching Example

<example for="teaching" language="go">
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
]]></example>

Taste: unexported field and parser create strongest practical invariant;
`error` signals invalid input, `bool` ordinary absence. Explicit control
flow beats imported monad vocabulary.

## Cost Guard

1. Replace recursion with iteration.
2. Closure or interface abstraction escapes on relevant path: named function
   and concrete types.
3. `map`/`filter` helper obscures allocation or control flow: retain algebra
   in pure helpers, use one explicit loop.
4. Confine unavoidable mutation to fresh local value; publish only completed
   valid result.
5. Preserve explicit error timing and partial-result contracts, context
   propagation, goroutine/channel ownership.

## Validation

Run formatting and static analysis when configured. Use existing benchmarks
and escape analysis for hot paths; otherwise report closure/allocation risk
as unmeasured.
