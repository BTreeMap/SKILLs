# Python Cost Model

## Disclosed Constraints

- No tail-call optimization. Unbounded structural recursion consumes one frame
  per element.
- Slicing, concatenation, eager intermediates, and transient wrappers increase
  allocation and GC pressure; recursive head/tail list code can become
  quadratic.
- `map`, `filter`, and generators are lazy and single-pass. Deferral changes
  exception timing, resource lifetime, and when effects occur.
- Python's type hints cannot make runtime input valid without boundary checks.

## Preferred FP Shapes

- Prefer explicit `map` and `filter` composition over equivalent comprehension
  syntax so the filter-transform algebra remains visible. Yield only when a
  named predicate, required concrete collection, or repository convention makes
  another form materially clearer.
- Use named curried helpers through `functools.partial` when partial application
  clarifies a reusable operation.
- Prefer generators for streaming and $O(1)$ auxiliary memory.
- Prefer `sum`, `any`, `all`, `min`, `max`, and `next` over generic reduction.
- Use `functools.reduce` only for a genuine fold with an explicit accumulator
  invariant.
- Represent closed states with frozen dataclasses, enums, tagged unions, and
  exhaustive type-checker-supported matching where project tooling permits.
- Represent optional/fallible flow with established project types or explicit
  return unions. Do not introduce a runtime monad hierarchy solely for syntax.

## Domain and Effect Constraints

- Python has no sealed algebraic data types. Approximate closed sums with
  dataclass variants plus a union and exhaustive type-checker-supported `match`;
  runtime closure is a project convention.
- Use `T | None` for expected absence. Use an established project `Result` type
  for expected failures only when present; otherwise return a small tagged union
  or raise at the imperative boundary according to local convention.
- Frozen dataclasses and tuples are only shallowly immutable. Copy or freeze
  nested values only at the ownership boundary that requires it.
- Put invariant checks in one parsing factory. A dataclass constructor cannot be
  made truly private, so document and type-check the construction convention.
- Keep files, locks, transactions, and generators inside `with`/`async with`.
  Use `asyncio.TaskGroup` where available for scoped child tasks; preserve
  cancellation rather than swallowing `CancelledError`.
- Run independent async effects concurrently only through a bounded, scoped
  mechanism; sequence dependent `await` calls explicitly when later inputs come
  from earlier outputs.
- Bound producer/consumer pipelines with finite iterators, semaphore limits, or
  bounded queues. Do not create every coroutine before applying a concurrency
  limit.

## Teaching Example

<teaching_example language="python"><![CDATA[
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Self, TypeGuard

@dataclass(frozen=True, slots=True)
class Email:
    value: str

  def __post_init__(self) -> None:
    if "@" not in self.value:
      raise ValueError("invalid email")

  @classmethod
  def parse(cls, raw: str) -> Self | None:
    normalized = raw.strip().lower()
    return cls(normalized) if "@" in normalized else None

def is_email(value: Email | None) -> TypeGuard[Email]:
    return value is not None

def email_value(email: Email) -> str:
    return email.value

def valid_emails(raw_values: Iterable[str]) -> Iterator[str]:
  return map(email_value, filter(is_email, map(Email.parse, raw_values)))
]]></teaching_example>

Taste: untrusted strings cross one smart-constructor boundary; absence is
explicit; the result streams. Named functions preserve type narrowing and domain
meaning; point-free cleverness would make this version worse. `__post_init__`
also protects direct construction because Python cannot hide the constructor.

## Cost Guard

1. Replace collection-sized recursion with an iterator or generator.
2. If the caller requires eager output, materialize exactly once at the public
   boundary.
3. If lazy conversion changes exception/effect timing or closes a resource too
   early, preserve eager evaluation inside the resource scope.
4. If a pipeline needs early exit or complex error recovery, use a native
   short-circuit primitive or a local loop with pure helpers.
5. If repeated lambdas hide domain meaning, name the predicate/projector; do not
   pursue point-free style past debuggability.
6. Preserve context-manager lifetime, task cancellation, transaction scope, and
  concurrency bounds across lazy or async refactors.

## Validation Focus

Test empty, large, one-shot iterator, and exception-producing inputs. Verify
whether callers require a list, reusable iterable, or lazy iterator. Measure
peak memory before claiming a streaming improvement.
