# TypeScript Cost Model

## Disclosed Constraints

- Runtime behavior is JavaScript: no portable TCO, possible intermediate arrays,
  closure allocation, identity semantics, and object-shape sensitivity.
- Discriminated unions, `readonly`, generics, and exhaustive checks are erased.
  They can remove representable invalid states at zero runtime representation
  cost, but they cannot validate unknown data.
- Deep conditional types and abstraction-heavy inference can impose substantial
  compiler and editor cost even when runtime cost is zero.
- Runtime `Option`/`Either` wrappers add values and allocations when a native
  discriminated union would suffice.

## Preferred FP Shapes

- Model mutually exclusive states with `readonly` discriminated unions.
- Make eliminators and transition functions total with exhaustive `switch`
  handling and a `never` proof consistent with repository conventions.
- Parse and validate external values before constructing trusted domain types.
- Use native arrays, promises, `async`/`await`, and project-standard result
  unions. Use `map`, `filter`, `some`, `every`, `find`, and `reduce` deliberately.
- Use branded/opaque types when they enforce a domain boundary without forcing
  unsafe assertions through the codebase.

## Domain and Effect Constraints

- Prefer an explicit `Option`/`Result` discriminated union when absence or failure
  is central to composition. Use `T | undefined` for local incidental absence;
  do not mix representations in one domain flow.
- Keep brands and union constructors module-private. A brand assertion belongs
  only inside the validating smart constructor, never at call sites.
- Use products for fields that coexist and sums for mutually exclusive states.
  Avoid optional-property bags whose combinations include impossible states.
- Treat exhaustive `switch` plus a `never` assertion as the elimination proof.
  Runtime decoders must reject unknown tags before the value enters the domain.
- Use `Promise.all` for independent bounded work and sequential `await` for
  dependent work. Propagate `AbortSignal` and release listeners/resources.
- Keep complex conditional types off broad public surfaces when named unions
  provide better compiler performance and diagnostics.

## React Through a Haskell-Trained Lens

- Derive the React version, renderer, server/client boundary, and state library
  from the project. Respect framework ownership of effects and serialization;
  do not move non-serializable values across a server/client boundary.
- Treat a component as a pure function from typed props and state to UI. Keep
  domain transitions independent of React and represent UI states/actions as
  `readonly` discriminated unions.
- Prefer a pure reducer when transitions form a state machine. Events should name
  domain facts (`submitted`, `succeeded`) rather than setter mechanics. Make both
  state and action matching exhaustive with a `never` proof.
- Derive values during render instead of duplicating state. Use effects only for
  external synchronization; put effects caused solely by a user event in that
  event handler.
- Keep dependency arrays truthful. Cleanup resources, propagate `AbortSignal`,
  and encode request identity so stale responses cannot create an invalid state.
- Use immutable updates and functional setters for prior-state dependencies.
  Avoid broad context values that cause unrelated consumers to rerender.
- Preserve semantic keys. Model mutually exclusive controlled/uncontrolled props
  as a union when the component API must forbid invalid combinations.
- Treat `useMemo`, `useCallback`, and `memo` as measured cost controls. They do
  not establish correctness and can retain values, complicate dependencies, and
  add comparison work.
- Use a custom hook as an effect interpreter only when it isolates lifecycle and
  cancellation. Keep the reducer, smart constructors, and selectors framework-
  free and directly testable.

<react_teaching_example language="typescript"><![CDATA[
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
]]></react_teaching_example>

React taste: discriminated unions remove contradictory loading/data/error fields;
the pure reducer encodes legal transitions and stale-response rejection; rendering
is total. Effects belong in a bounded, abortable handler or hook around this core.

## Teaching Example

<teaching_example language="typescript"><![CDATA[
declare const portBrand: unique symbol;
type Port = number & { readonly [portBrand]: true };
type Result<T, E> =
  | { readonly tag: "ok"; readonly value: T }
  | { readonly tag: "error"; readonly error: E };

const parsePort = (n: number): Result<Port, string> =>
  Number.isInteger(n) && n > 0 && n <= 65535
    ? { tag: "ok", value: n as Port }
    : { tag: "error", error: "invalid port" };

const foldResult = <T, E, R>(
  result: Result<T, E>,
  onOk: (value: T) => R,
  onError: (error: E) => R,
): R => result.tag === "ok" ? onOk(result.value) : onError(result.error);
]]></teaching_example>

Taste: the sole assertion sits behind validation, `Result` exposes expected
failure, and consumers eliminate both variants. Types disappear at runtime, so
external input still requires parsing.

## Cost Guard

1. Replace unbounded recursion with iteration or native collection operations.
2. Replace a runtime monadic wrapper with an erased/native union when it carries
   no behavior unavailable from functions.
3. If a callback chain creates measured intermediate cost, fuse one level.
4. If a type-level encoding degrades compiler responsiveness or diagnostics,
   simplify to explicit named unions and functions.
5. Preserve JavaScript evaluation, identity, and async ordering semantics.
6. Preserve abort propagation, cleanup, bounded fan-out, transaction scope, and
  runtime decoding at external boundaries.

## Validation Focus

Run typechecking and focused runtime tests. Test every union variant, invalid
external input, exhaustive branches, and async rejection/cancellation behavior.
Treat a passing typecheck as evidence of internal consistency, not input safety.
