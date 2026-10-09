# Python Profile

## Cost Model

- Python-level loop costs roughly 50 to 100 ns per iteration; `str` methods,
  `bytes.translate`, `re` run in C at 1 to 5 ns per character. Linear
  complexity necessary, not sufficient: per-character `for` loop is wrong
  backend even at O(n). Scan with `find`, `split`, `partition`, `translate`,
  or compiled pattern; keep Python iteration proportional to tokens
  produced, never characters read.
- Backtracking engine is linear on unambiguous pattern, exponential on
  ambiguous one. Nested or adjacent quantifiers over overlapping classes
  (`(a+)+`, `[\w.]+@`) and `\s*` under `re.MULTILINE` are blow-up shapes;
  one character class with one quantifier is safe. Untrusted or
  agent-supplied patterns need length cap regardless; `re` has no timeout.
- No tail-call optimization. Unbounded structural recursion consumes one
  frame per element.
- Slicing, concatenation, eager intermediates, transient wrappers increase
  allocation and GC pressure; recursive head/tail list code can become
  quadratic.
- `map`, `filter`, generators are lazy and single-pass. Deferral changes
  exception timing, resource lifetime, when effects occur.
- Type hints cannot make runtime input valid without boundary checks.

## Domain Shapes

- Python has no sealed algebraic data types. Approximate closed sums with
  frozen dataclass variants, enums, or tagged unions plus union and
  exhaustive type-checker-supported `match` where project tooling permits;
  runtime closure is project convention.
- `T | None` for expected absence. Expected failure: established project
  `Result` type only when present; otherwise small tagged union or raise at
  imperative boundary per local convention. No runtime monad hierarchy
  solely for syntax.
- Invariant checks in one parsing factory. Dataclass constructor cannot be
  made truly private: document and type-check construction convention.
- Frozen dataclasses and tuples only shallowly immutable. Copy or freeze
  nested values only at ownership boundary that requires it.
- Prefer explicit `map` and `filter` composition over equivalent
  comprehension syntax so filter-transform algebra stays visible. Yield only
  when named predicate, required concrete collection, or repository
  convention makes another form materially clearer.
- Prefer `sum`, `any`, `all`, `min`, `max`, `next` over generic reduction;
  `functools.reduce` only for genuine fold with explicit accumulator
  invariant.
- Generators for streaming and $O(1)$ auxiliary memory. Named curried
  helpers through `functools.partial` when partial application clarifies
  reusable operation.

## Effects

- Keep files, locks, transactions, generators inside `with`/`async with`.
- `asyncio.TaskGroup` where available for scoped child tasks; preserve
  cancellation, never swallow `CancelledError`.
- Bound producer/consumer pipelines with finite iterators, semaphore limits,
  or bounded queues. Do not create every coroutine before applying
  concurrency limit.

## Teaching Example

<example for="teaching" language="python">
<![CDATA[
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
]]></example>

Taste: untrusted strings cross one smart-constructor boundary; absence
explicit; result streams. Named functions preserve type narrowing and domain
meaning; point-free cleverness would make this version worse.
`__post_init__` also protects direct construction, since Python cannot hide
constructor.

## Cost Guard

1. Replace collection-sized recursion with iterator or generator.
2. Caller requires eager output: materialize exactly once at public
   boundary.
3. Lazy conversion changes exception/effect timing or closes resource too
   early: preserve eager evaluation inside resource scope.
4. Pipeline needs early exit or complex error recovery: native short-circuit
   primitive or local loop with pure helpers.
5. Repeated lambdas hide domain meaning: name predicate/projector; do not
   pursue point-free past debuggability.
6. Preserve context-manager lifetime and task cancellation across lazy or
   async refactors.

## Validation

Test empty, large, one-shot iterator, exception-producing inputs. Verify
whether callers require list, reusable iterable, or lazy iterator. Measure
peak memory before claiming streaming improvement.
