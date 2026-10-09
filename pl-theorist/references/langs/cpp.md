# C++ Profile

## Cost Model

- Derive language standard and library availability from build. Do not
  assume ranges, coroutines, concepts, or `std::expected` when target does
  not provide them.
- Templates and standard algorithms can be zero-overhead abstractions, but
  code size, compile time, iterator category, proxy references, captures,
  type erasure, allocation remain material.
- Value semantics, moves, copies, exceptions, destruction order, aliasing
  are observable. `const` and `const` methods do not imply deep
  immutability.
- Recursive algorithms lack guaranteed TCO. Lazy range views can dangle when
  they outlive borrowed sources.

## Domain Shapes

- `std::variant` for closed sums, structs/tuples for products,
  `std::optional` for absence, `std::expected` for expected failure when
  configured standard provides it. Otherwise project's result type or small
  `std::variant<T, E>`.
- Visit every `variant` alternative with overload set or exhaustive visitor.
  Avoid `get` when `get_if`, `visit`, or proven state is total.
- Classes with private representation and static factories for refined
  values. Constructors private when construction can fail. Successful object
  must satisfy its invariant; temporarily invalid object "finished" later is
  defect. Prefer value semantics.
- Standard algorithms/ranges when they clarify intent and preserve traversal
  and allocation cost. Prefer `transform_reduce`, `any_of`, `all_of`,
  `find_if` over generic fold when they name algebra.
- Capture lambdas narrowly, by value/reference deliberately. Avoid
  `std::function` when template parameter or concrete callable avoids type
  erasure and allocation.

## Effects

- RAII guards and deterministic destruction for memory, files, locks,
  transactions. Never let view, span, iterator, callback, or coroutine frame
  outlive its owner.
- Futures/coroutines only through project-standard executors and
  cancellation facilities; core language provides no universal structured
  concurrency. Distinguish independent scheduled work from dependent
  continuation chains; preserve executor and exception aggregation
  semantics.
- Mark functions `noexcept` only when complete call graph contract supports
  it; unexpected throw then terminates process.

## Teaching Example

```cpp
#include <cstdint>
#include <variant>

enum class PortError { out_of_range };

class Port {
public:
    static std::variant<Port, PortError> parse(unsigned value) {
        if (value == 0 || value > UINT16_MAX) {
            return PortError::out_of_range;
        }
        return Port{static_cast<std::uint16_t>(value)};
    }

    std::uint16_t value() const noexcept { return value_; }

private:
    explicit Port(std::uint16_t value) : value_(value) {}
    std::uint16_t value_;
};
```

Taste: private construction makes invalid ports unrepresentable; `variant`
provides C++17 result without dependencies. C++23 `std::expected` already
available: prefer it for same domain meaning.

## Cost Guard

1. Replace unbounded recursion with algorithms, iterators, or direct loop.
2. Inspect copies, moves, allocations, type erasure, iterator invalidation,
   borrowed-range lifetimes.
3. Fuse passes only when profiling or data size justifies readability cost.
4. Prefer stack/value representation, but do not enlarge hot variants or
   copy large aggregates blindly; measure layout and ownership choices.
5. Preserve RAII destruction order, exception safety guarantee, executor
   affinity.

## Validation

Build under configured standard with warnings, static analysis, sanitizers
when available. Test every variant, factory boundary, move/copy path,
exception guarantee, lifetime edge, cancellation path. Benchmark before
claiming algorithm/range abstraction or hand-written loops are faster.
