# C Profile

## Cost Model

- C has no algebraic data types, closures, exceptions, ownership checker, or
  standard `Option`/`Result`.
- Function pointers inhibit inlining in some toolchains; callback-heavy
  generic pipelines can cost more and obscure ownership compared with direct
  loop.
- Values, pointers, lengths, allocation provenance, aliasing, lifetimes are
  part of contract. `const` prevents mutation through one access path; does
  not prove deep immutability.
- Signed overflow undefined; allocation can fail; unchecked indexing, null
  dereference, use-after-free, data races are defects.

## Domain Shapes

- Encode sums explicitly as tag plus union, products as structs. Give each
  tagged union constructor and eliminator one responsibility. Switch on
  every enum variant; enable compiler warnings for missing cases; keep
  defensive policy for corrupted/untrusted tags.
- Immutable-by-convention value structs, small pure functions, constructor
  functions establishing invariants atomically. Hide struct definitions in
  implementation files when callers must not forge refined value.
  Representation public: every public operation must defensively preserve
  and check invariant.
- Return struct such as `{ bool has_value; T value; }` for ordinary absence,
  tagged result union for expected failure. Never read inactive union arm.
- Express `map`/`filter`/`fold` conceptually, but implement hot collection
  work as counted single-pass loop with named predicate/projector/step.

## Effects

- Make ownership visible in names, documentation, signatures: borrowed,
  transferred, retained, or returned. Pair each successful acquisition with
  exactly one release on every path.
- Pass allocator and ownership policy explicitly where allocation crosses
  API boundary. Prefer caller-owned buffers when that is established
  convention.
- Cleanup labels or one well-structured exit path when multiple acquisitions
  require rollback. Preserve lock and transaction order.
- Propagate cancellation through project's explicit token/flag mechanism.
  Bound queues, threads, retries, buffers; C supplies no structured
  concurrency automatically.
- Keep I/O, volatile/device access, atomics, logging, mutation outside pure
  calculations; algebraic laws never license reordering them.

## Teaching Example

<example for="teaching" language="c">
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
]]></example>

Taste: tag makes failure explicit; constructor is sole admission path in
this translation unit. C cannot prevent callers forging public `Port`; use
opaque type when invariant must be enforced across modules.

## Cost Guard

1. Reject unbounded recursion; loop with explicit invariant.
2. Fuse collection passes when extra buffers or callback dispatch are
   material.
3. Check all size arithmetic before allocation, all narrowing conversions
   before construction.
4. Keep aliasing and ownership simple enough for humans and optimizer to
   reason about; `restrict` only when its contract is proved.
5. Preserve cleanup, lock, atomic, error paths.

## Validation

Compile with repository's strict warnings and sanitizers when configured.
Test every tag, boundary value, allocation failure path, cleanup path,
aliasing contract, cancellation path, integer conversion. Measure before
replacing clear loop with callbacks or additional allocation.
