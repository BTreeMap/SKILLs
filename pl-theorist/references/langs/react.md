# React Through a Haskell-Trained Lens

Loaded beside `javascript` or `typescript` when code uses React.

## Rules

- Derive React version, renderer, server/client boundary, state library from
  project. Introduce no experimental APIs or state framework to imitate
  Haskell. Respect framework ownership of effects and serialization; move no
  non-serializable values across server/client boundary.
- Rendering is pure function from props and state to UI. Never perform I/O,
  mutation, subscription, timer creation, or state updates during render.
- Model component state as stable tagged variants, not interacting booleans
  and nullable fields; in TypeScript, UI states and actions as `readonly`
  discriminated unions. Prefer pure reducer when transitions form state
  machine, with event-shaped actions naming domain facts (`submitted`,
  `succeeded`) over setter mechanics. In TypeScript, make both state and
  action matching exhaustive with `never` proof.
- Derive values during render instead of synchronizing redundant state in
  effect; duplicate nothing into state. Effects only to synchronize with
  external system. Effect caused solely by user event goes in that event
  handler.
- Keep effect dependencies honest. Clean up subscriptions and timers,
  propagate `AbortSignal`, encode request identity so stale async
  completions cannot create invalid state.
- Update immutably with structural sharing. Functional state updates when
  next value depends on previous. Never mutate props, reducer state, or
  context values. Avoid broad context values that rerender unrelated
  consumers.
- Keys are semantic identity. No array indexes for reorderable or stateful
  lists. In TypeScript, model mutually exclusive controlled/uncontrolled
  props as union when component API must forbid invalid combinations.
- `useMemo`, `useCallback`, `memo` are measured cost controls, not
  correctness tools. Add only for measured expensive work, required
  referential stability, or demonstrated render boundary; they can retain
  values, complicate dependencies, add comparison work.
- Narrowly named custom hook as effect interpreter only when it isolates
  lifecycle and cancellation. Keep domain transitions, reducer, smart
  constructors, selectors framework-free and testable without React.

## Teaching Example

```typescript
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
```

In JavaScript, same code drops type declarations, freezes initial state
(`Object.freeze({ tag: "idle" })`), replaces each `assertNever` call with
`default` arm throwing `TypeError`.

Taste: one tag defines each valid UI state, removing contradictory
loading/data/error fields; pure reducer encodes legal transitions, rejects
stale responses by request identity; rendering eliminates every known
variant. Effects belong in bounded, abortable handler or hook around this
core.
