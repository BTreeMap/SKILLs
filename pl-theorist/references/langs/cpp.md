# C++ Cost Model

## Disclosed Constraints

- Derive the language standard and library availability from the build. Do not
  assume ranges, coroutines, concepts, or `std::expected` when the target does not
  provide them.
- Templates and standard algorithms can be zero-overhead abstractions, but code
  size, compile time, iterator category, proxy references, captures, type erasure,
  and allocation remain material.
- Value semantics, moves, copies, exceptions, destruction order, and aliasing are
  observable. `const` and `const` methods do not imply deep immutability.
- Recursive algorithms lack guaranteed TCO. Lazy range views can dangle when they
  outlive borrowed sources.

## Preferred FP Shapes

- Use `std::variant` for closed sums, structs/tuples for products,
  `std::optional` for absence, and `std::expected` for expected failure when the
  configured standard provides it. Otherwise use the project's result type or a
  small `std::variant<T, E>`.
- Use classes with private representation and static factories for refined
  values. Prefer value semantics, RAII, and deterministic destruction.
- Use standard algorithms/ranges when they clarify intent and preserve traversal
  and allocation cost. Prefer `transform_reduce`, `any_of`, `all_of`, and
  `find_if` over a generic fold when they name the algebra.
- Capture lambdas narrowly and by value/reference deliberately. Avoid
  `std::function` when a template parameter or concrete callable avoids type
  erasure and allocation.
- Use futures/coroutines only through project-standard executors and cancellation
  facilities; the core language does not provide universal structured
  concurrency.

## Domain and Effect Constraints

- Visit every `variant` alternative with an overload set or exhaustive visitor.
  Avoid `get` when `get_if`, `visit`, or a proven state is total.
- Keep constructors private when construction can fail. A successful object must
  satisfy its invariant; do not create a temporarily invalid object and “finish”
  it later.
- Use RAII guards for memory, files, locks, and transactions. Never let a view,
  span, iterator, callback, or coroutine frame outlive its owner.
- Distinguish independent scheduled work from dependent continuation chains.
  Bound fan-out and preserve executor, cancellation, exception aggregation, and
  transaction semantics.
- Mark functions `noexcept` only when the complete call graph contract supports
  it; an unexpected throw then terminates the process.

## Teaching Example

<teaching_example language="cpp"><![CDATA[
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
]]></teaching_example>

Taste: private construction makes invalid ports unrepresentable; `variant`
provides a C++17 result without dependencies. If C++23 `std::expected` is already
available, prefer it for the same domain meaning.

## Cost Guard

1. Replace unbounded recursion with algorithms, iterators, or a direct loop.
2. Inspect copies, moves, allocations, type erasure, iterator invalidation, and
   borrowed-range lifetimes.
3. Fuse passes only when profiling or data size justifies the readability cost.
4. Prefer stack/value representation, but do not enlarge hot variants or copy
   large aggregates blindly; measure layout and ownership choices.
5. Preserve RAII destruction order, exception safety guarantee, cancellation,
   executor affinity, and transaction scope.

## Validation Focus

Build under the configured standard with warnings, static analysis, sanitizers,
and focused tests when available. Test every variant, factory boundary, move/copy
path, exception guarantee, lifetime edge, and cancellation path. Benchmark before
claiming algorithm/range abstraction or hand-written loops are faster.
