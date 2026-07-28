# JavaScript ES6+ Cost Model

## Disclosed Constraints

- Assume broad ES6 availability. Do not rely on portable tail-call optimization.
- JIT engines favor stable, flat object shapes and native arrays. Deep immutable
  wrappers and inconsistent property layouts can inhibit optimization and make
  debugging opaque.
- `filter().map()` creates an intermediate array; callbacks and captured
  closures may allocate. This matters only when scale or measurement makes it
  material.
- Refactors can change `this`, sparse-array behavior, identity, thrown-error
  timing, and promise/microtask order.

## Preferred FP Shapes

- Use native array and iterator primitives with curried predicates/projectors.
- Use `const`, replacement values, flat stable objects, and discriminant fields.
- Use promises and `async`/`await` as native effect sequencing. Preserve
  concurrency intentionally: sequential `await`, `Promise.all`, and
  `Promise.allSettled` are different algebras.
- Prefer `some`/`every`/`find` and native aggregation where available; otherwise
  use `reduce` with a named accumulator law.
- Prefer plain tagged result objects already used by the project over custom
  `Pipe`, `Map`, `Option`, or immutable-wrapper frameworks.

## Domain and Effect Constraints

- JavaScript cannot statically close a sum type. Use stable discriminant fields,
  factories, module-private constructors, and total eliminator functions to
  enforce the protocol at runtime.
- Represent expected absence with `null` only when the project uses it
  consistently. For expected failure, prefer a flat frozen `{ tag, value/error }`
  result object over exceptions inside the pure core.
- `Object.freeze` is shallow. Prefer fresh flat values and disciplined ownership;
  do not recursively freeze hot object graphs without evidence.
- Distinguish independent `Promise.all` composition from dependent sequential
  `await`. Bound fan-out rather than creating an unbounded promise array.
- Propagate `AbortSignal`; remove listeners and release resources with
  `try/finally` or native explicit-resource-management support when the runtime
  target guarantees it.
- Preserve idempotency, transaction boundaries, and diagnostic context when
  retrying promise-based effects.

## React Through a Haskell-Trained Lens

- Derive the React version, renderer, server/client boundary, and state library
  from the project. Do not introduce experimental APIs or a state framework to
  imitate Haskell.
- Treat rendering as a pure function from props and state to UI. Never perform
  I/O, mutation, subscription, timer creation, or state updates during render.
- Model component state as stable tagged variants instead of interacting booleans
  and nullable fields. Use event-shaped actions and a pure reducer; factories and
  runtime checks compensate for JavaScript's open object model.
- Derive values during render rather than synchronizing redundant state in an
  effect. Use effects only to synchronize with an external system. Put
  user-triggered effects in event handlers when no render synchronization exists.
- Keep effect dependencies honest. Cleanup subscriptions and timers, propagate
  `AbortSignal`, and reject stale async completions with a request identity or
  equivalent protocol.
- Update immutably with structural sharing. Use functional state updates when the
  next value depends on the previous value. Never mutate props, reducer state, or
  context values.
- Treat keys as semantic identity. Do not use array indexes for reorderable or
  stateful lists.
- `useMemo`, `useCallback`, and `memo` are performance tools, not semantic tools.
  Add them only for measured expensive work, required referential stability, or
  a demonstrated render boundary; account for dependency and retention cost.
- Encapsulate effect interpreters in narrowly named custom hooks, but keep domain
  transitions as ordinary pure functions that can be tested without React.

<react_teaching_example language="javascript"><![CDATA[
const initialState = Object.freeze({ tag: "idle" });

function searchReducer(state, action) {
  switch (action.type) {
    case "requested":
      return { tag: "loading", requestId: action.requestId };
    case "succeeded":
      return state.tag === "loading" && state.requestId === action.requestId
        ? { tag: "loaded", items: action.items }
        : state;
    case "failed":
      return state.tag === "loading" && state.requestId === action.requestId
        ? { tag: "failed", message: action.message }
        : state;
    default:
      throw new TypeError("unknown search action");
  }
}

function SearchStatus({ state }) {
  switch (state.tag) {
    case "idle": return <p>Enter a query.</p>;
    case "loading": return <p>Loading…</p>;
    case "loaded": return <ResultList items={state.items} />;
    case "failed": return <p role="alert">{state.message}</p>;
    default: throw new TypeError("unknown search state");
  }
}

function useSearch(query) {
  const [state, dispatch] = useReducer(searchReducer, initialState);
  useEffect(() => {
    if (query === "") return;
    const controller = new AbortController();
    const requestId = crypto.randomUUID();
    dispatch({ type: "requested", requestId });
    search(query, controller.signal).then(
      items => dispatch({ type: "succeeded", requestId, items }),
      error => {
        if (!controller.signal.aborted) {
          dispatch({ type: "failed", requestId, message: String(error) });
        }
      },
    );
    return () => controller.abort();
  }, [query]);
  return state;
}
]]></react_teaching_example>

React taste: one tag defines each valid UI state; the reducer is a pure state
transition; request identity rejects stale effects; rendering eliminates every
known variant. JavaScript still needs runtime defensive branches.

## Teaching Example

<teaching_example language="javascript"><![CDATA[
const ok = value => Object.freeze({ tag: "ok", value });
const failure = message => Object.freeze({ tag: "error", message });

const parsePort = value => {
  const port = Number(value);
  return Number.isInteger(port) && port > 0 && port <= 65535
    ? ok(port)
    : failure("invalid port");
};

const describe = result => {
  switch (result.tag) {
    case "ok": return `port ${result.value}`;
    case "error": return result.message;
    default: throw new TypeError("unknown result variant");
  }
};
]]></teaching_example>

Taste: factories admit only valid ports, the tagged result makes failure data,
and flat stable objects suit the engine. Runtime JavaScript cannot prove that no
third tag exists, so boundary validation remains mandatory.

## Cost Guard

1. Replace recursive collection traversal with native iteration.
2. Use native `filter().map()` for ordinary code. If the intermediate array is
   measured as material, descend to one `reduce` or a direct loop with pure
   helpers.
3. Keep output object fields present and consistently ordered where the hot path
   depends on stable shapes.
4. If currying creates opaque closure towers or material allocation, use named
   unary/binary helpers.
5. Preserve synchronous versus deferred effects and exact promise concurrency.
6. Preserve abort propagation, cleanup, transaction scope, and bounded fan-out.

## Validation Focus

Test empty and sparse arrays, object identity, mutation visibility, exception
timing, promise ordering, and representative hot-path sizes. Do not claim V8 or
SpiderMonkey optimization without measurement or engine evidence.