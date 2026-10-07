# Response-to-reviewer mapping

Stage 9 deliverable for `rebut`, alongside the rebuttal draft or revision
letter.

## Input

The user supplies the reviews as text: per reviewer, the quoted concerns and
the score, in any readable layout. Paste them in one block per reviewer:

<template for="review-input">
- Reviewer <id> (score <n>): <quoted concerns>
</template>

## Mapping

<template for="mapping">
| Reviewer | Concern (quoted one-liner) | Class | Response location | Change made |
|----------|----------------------------|-------|-------------------|-------------|
| | | | | |
</template>

Classes follow the `rebuttal-playbook` triage: misunderstanding, missing
evidence, scope or taste disagreement, reviewer factual error.

## AC-facing summary

Per reviewer, the score trajectory and what changed; map every accepted
point to its revision location. The AC reads the whole record, so this
table is the deliverable of last resort.
