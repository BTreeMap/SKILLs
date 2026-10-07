# React Through a Haskell-Trained Lens

Loaded beside `javascript` or `typescript` when the code uses React.

## Rules

- Derive the React version, renderer, server/client boundary, and state
  library from the project. Do not introduce experimental APIs or a state
  framework to imitate Haskell. Respect framework ownership of effects and
  serialization; do not move non-serializable values across a server/client
  boundary.
- Treat rendering as a pure function from props and state to UI. Never
  perform I/O, mutation, subscription, timer creation, or state updates
  during render.
- Model component state as stable tagged variants instead of interacting
  booleans and nullable fields; in TypeScript, represent UI states and
  actions as `readonly` discriminated unions. Prefer a pure reducer when
  transitions form a state machine, with event-shaped actions that name
  domain facts (`submitted`, `succeeded`) over setter mechanics. In
  TypeScript, make both state and action matching exhaustive with a `never`
  proof.
- Derive values during render rather than synchronizing redundant state in
  an effect; duplicate nothing into state. Use effects only to synchronize
  with an external system. Put an effect caused solely by a user event in
  that event handler.
- Keep effect dependencies honest. Clean up subscriptions and timers,
  propagate `AbortSignal`, and encode request identity so stale async
  completions cannot create an invalid state.
- Update immutably with structural sharing. Use functional state updates
  when the next value depends on the previous value. Never mutate props,
  reducer state, or context values. Avoid broad context values that cause
  unrelated consumers to rerender.
- Treat keys as semantic identity. Do not use array indexes for reorderable
  or stateful lists. In TypeScript, model mutually exclusive
  controlled/uncontrolled props as a union when the component API must
  forbid invalid combinations.
- `useMemo`, `useCallback`, and `memo` are measured cost controls, not
  correctness tools. Add them only for measured expensive work, required
  referential stability, or a demonstrated render boundary; they can retain
  values, complicate dependencies, and add comparison work.
- Use a narrowly named custom hook as an effect interpreter only when it
  isolates lifecycle and cancellation. Keep domain transitions, the reducer,
  smart constructors, and selectors framework-free and testable without
  React.

## Teaching Example

<example for="teaching" framework="react" language="typescript">
<![CDATA[
type SearchState =
  | { readonly tag: "idle" }
  | { readonly tag: "loading"; readonly requestId: string }
  | { readonly tag: "loaded"; readonly items: readonly Item[] }
  | { readonly tag: "failed"; readonly message: string };

type SearchAction =
  | { readonly type: "requested"; readonly requestId: string }
  | { readonly type: "succeeded"; readonly requestId: string; readonly items: readonly Item[] }
  | { readonly type: "failed"; readonly requestId: string; readonly message: string };

const searchReducer = (state: SearchState, action: SearchAction): SearchState => {
  switch (action.type) {
    case "requested": return { tag: "loading", requestId: action.requestId };
    case "succeeded": return state.tag === "loading" && state.requestId === action.requestId
      ? { tag: "loaded", items: action.items } : state;
    case "failed": return state.tag === "loading" && state.requestId === action.requestId
      ? { tag: "failed", message: action.message } : state;
    default: return assertNever(action);
  }
};

const assertNever = (value: never): never => {
  throw new TypeError(`unexpected variant: ${String(value)}`);
};

const SearchStatus = ({ state }: { readonly state: SearchState }) => {
  switch (state.tag) {
    case "idle": return <p>Enter a query.</p>;
    case "loading": return <p>Loading…</p>;
    case "loaded": return <ResultList items={state.items} />;
    case "failed": return <p role="alert">{state.message}</p>;
    default: return assertNever(state);
  }
};

const useSearch = (query: string): SearchState => {
  const [state, dispatch] = useReducer(searchReducer, { tag: "idle" });
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
};
]]></example>

In JavaScript, the same code drops the type declarations, freezes the
initial state (`Object.freeze({ tag: "idle" })`), and replaces each
`assertNever` call with a `default` arm that throws a `TypeError`.

Taste: one tag defines each valid UI state, removing contradictory
loading/data/error fields; the pure reducer encodes legal transitions and
rejects stale responses by request identity; rendering eliminates every
known variant. Effects belong in a bounded, abortable handler or hook around
this core.
