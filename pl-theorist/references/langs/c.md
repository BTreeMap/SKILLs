# C Cost Model

## Disclosed Constraints

- C has no algebraic data types, closures, exceptions, ownership checker, or
  standard `Option`/`Result`. Encode sums explicitly as a tag plus a union and
  products as structs.
- Function pointers inhibit inlining in some toolchains; callback-heavy generic
  pipelines can cost more and obscure ownership compared with a direct loop.
- Values, pointers, lengths, allocation provenance, aliasing, and lifetimes are
  part of the contract. `const` prevents mutation through one access path; it
  does not prove deep immutability.
- Signed overflow is undefined, allocation can fail, and unchecked indexing,
  null dereference, use-after-free, and data races are defects.

## Preferred FP Shapes

- Use immutable-by-convention value structs, small pure functions, explicit
  tagged unions, and constructor functions that establish invariants atomically.
- Return a struct such as `{ bool has_value; T value; }` for ordinary absence and
  a tagged result union for expected failure. Never read an inactive union arm.
- Express `map`/`filter`/`fold` conceptually, but implement hot collection work as
  a counted single-pass loop with a named predicate/projector/step.
- Pass allocator and ownership policy explicitly where allocation crosses an API
  boundary. Prefer caller-owned buffers when that is the established convention.
- Use cleanup labels or one well-structured exit path when multiple acquisitions
  require rollback. Preserve lock and transaction order.

## Domain and Effect Constraints

- Hide struct definitions in implementation files when callers must not forge a
  refined value. If the representation is public, every public operation must
  defensively preserve and check the invariant.
- Give each tagged union constructor and eliminator one responsibility. Switch on
  every enum variant; enable compiler warnings for missing cases and keep a
  defensive policy for corrupted/untrusted tags.
- Make ownership visible in names, documentation, and signatures: borrowed,
  transferred, retained, or returned. Pair each successful acquisition with
  exactly one release on every path.
- Propagate cancellation through the project's explicit token/flag mechanism.
  Bound queues, threads, retries, and buffers; C supplies no structured
  concurrency automatically.
- Keep I/O, volatile/device access, atomics, logging, and mutation outside pure
  calculations; algebraic laws never license reordering them.

## Teaching Example

<teaching-example language="c">
<![CDATA[
#include <stdbool.h>
#include <stdint.h>

typedef struct { uint16_t value; } Port;
typedef enum { PORT_OK, PORT_OUT_OF_RANGE } PortResultTag;
typedef struct {
    PortResultTag tag;
    union { Port port; } data;
} PortResult;

static PortResult port_parse(unsigned value) {
    if (value == 0 || value > UINT16_MAX) {
        return (PortResult){ .tag = PORT_OUT_OF_RANGE };
    }
    return (PortResult){
        .tag = PORT_OK,
        .data.port = { .value = (uint16_t)value },
    };
}
]]></teaching-example>

Taste: the tag makes failure explicit and the constructor is the sole admission
path in this translation unit. C cannot prevent callers from forging a public
`Port`; use an opaque type when that invariant must be enforced across modules.

## Cost Guard

1. Reject unbounded recursion; use a loop with an explicit invariant.
2. Fuse collection passes when extra buffers or callback dispatch are material.
3. Check all size arithmetic before allocation and all narrowing conversions
   before construction.
4. Keep aliasing and ownership simple enough for both humans and optimizer to
   reason about; use `restrict` only when its contract is proved.
5. Preserve cleanup, lock, atomic, transaction, cancellation, and error paths.

## Validation Focus

Compile with the repository's strict warnings and sanitizers when configured.
Test every tag, boundary value, allocation failure path, cleanup path, aliasing
contract, cancellation path, and integer conversion. Measure before replacing a
clear loop with callbacks or additional allocation.
