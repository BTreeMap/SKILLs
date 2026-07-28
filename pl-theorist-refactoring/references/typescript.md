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

## Cost Guard

1. Replace unbounded recursion with iteration or native collection operations.
2. Replace a runtime monadic wrapper with an erased/native union when it carries
   no behavior unavailable from functions.
3. If a callback chain creates measured intermediate cost, fuse one level.
4. If a type-level encoding degrades compiler responsiveness or diagnostics,
   simplify to explicit named unions and functions.
5. Preserve JavaScript evaluation, identity, and async ordering semantics.

## Validation Focus

Run typechecking and focused runtime tests. Test every union variant, invalid
external input, exhaustive branches, and async rejection/cancellation behavior.
Treat a passing typecheck as evidence of internal consistency, not input safety.