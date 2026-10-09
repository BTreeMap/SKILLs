# Haskell Profile

## Cost Model

- Laziness supports composition and streaming but can retain input or build
  thunks, producing space leaks.
- Strictness is semantic and operational. Forcing too little harms
  accumulation; forcing too much can destroy productivity or infinite-stream
  behavior.
- List/stream fusion depends on exact producers, consumers, rewrite rules,
  optimization settings; point-free syntax guarantees none of it.
- Monad transformer stacks and generalized effects can improve composition
  while worsening inference, errors, allocation, operational visibility.

## Domain Shapes

- Algebraic data types, total pattern matching, pure functions, currying,
  point-free composition by default.
- `data` for sums/products, `newtype` for zero-cost semantic distinctions.
  Hide constructors, export smart constructors when values carry invariants.
- `Maybe` for expected absence, `Either DomainError` for expected failure.
  Avoid `Maybe` when callers need to know why construction failed.
- Keep exported paths free of partial functions unless type or constructor
  proves their preconditions. Eliminate partial list functions from
  production paths with `NonEmpty`, total folds, or pattern matching at
  refinement boundary.
- Derive or define instances only when their laws hold. State
  `Semigroup`/`Monoid` identity and associativity before using `foldMap` or
  parallel reduction.
- Prefer `foldMap` when monoid states aggregation, `traverse` when effects
  preserve shape, `foldl'` for strict left accumulation.

## Effects

- `Maybe`, `Either`, `IO`, established project effects, applicative
  traversal, monadic bind per dependency structure. Applicative structure
  does not itself promise parallel execution.
- Project's existing streaming and effect abstractions over competing
  transformer stack.
- `bracket`/`finally` or project's resource abstraction. Scope async work,
  propagate cancellation, use bounded queues/streaming combinators.
- Retries and transactions in effect interpreter; require idempotency or
  transaction before replaying effects.

## Teaching Example

<example for="teaching" language="haskell">
<![CDATA[
module Port (Port, PortError(..), mkPort, configuredPort) where

newtype Port = Port Int
  deriving (Eq, Show)

data PortError = PortOutOfRange
  deriving (Eq, Show)

mkPort :: Int -> Either PortError Port
mkPort n
  | n >= 1 && n <= 65535 = Right (Port n)
  | otherwise = Left PortOutOfRange

configuredPort :: Maybe Int -> Either PortError Port
configuredPort = maybe (mkPort 8080) mkPort
]]></example>

Taste: hide `Port` outside module, making smart constructor only admission
path. `Maybe` means absent configuration; `Either` preserves reason
construction failed; `maybe` eliminates absence totally.

## Cost Guard

1. Check whether consumers stream, retain input spine, or build accumulator
   thunks.
2. Introduce only narrowest strictness annotation, strict field, `foldl'`,
   or streaming fold needed.
3. Point-free composition hides sharing, strictness, or resource lifetime:
   restore named arguments and bindings.
4. Effect stack obscures types or profiling: simplify to established base
   effect or explicit interpreter.
5. Require profiling evidence before asserting fusion or allocation
   behavior.
6. Preserve bracketed resources and strictness/productivity under chosen
   effect interpreter.

## Validation

Test finite and infinite producers when productivity is contractual. Use
existing time/space profiling for strictness-sensitive paths; inspect
exception/resource behavior in `IO`.
