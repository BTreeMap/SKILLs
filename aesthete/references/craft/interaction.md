# Craft: interaction

## Principles

Cite only where they apply.

* **Targets**: acquisition difficulty rises as targets get smaller and
  farther. Frequent actions get large, close targets. Screen edges and
  corners effectively infinite in depth: premium real estate.
* **Choices**: decision time rises with number and complexity of options.
  Reduce, group, order by frequency, default. Ten equally weighted options
  is harder screen than three plus disclosure.
* **Convention**: users form expectations from every other interface they
  use. Departing from convention costs comprehension; must buy something
  real.
* **Conservation of complexity**: task's irreducible complexity goes
  somewhere. Put it in system.
* **Response threshold**: interactions completing within roughly four tenths
  of a second preserve sense of direct manipulation. Past that user notices
  waiting; attention starts to drift.
* **Memory**: recognition cheap, recall expensive. Show options.
* **Beauty bias**: attractive interfaces rated more usable; their problems
  go unreported. Test interaction separately from visual polish.

## The complete state set

Every interactive element ships these states; never ship happy path alone.

| State | Requirement |
| --- | --- |
| Rest | Affordance visible without hover. |
| Hover | Pointer only. Provide its information and actions through another channel; hover is invisible to touch and keyboard. |
| Focus-visible | Always present, never suppressed, high contrast, not clipped. Obscuring rules in `a11y`. |
| Active | Immediate acknowledgment at press, before any network work begins. |
| Disabled | Rare, always explained. Prefer enabled with explanation on attempt. |
| Loading | In place, label preserved so control does not resize. |
| Error | Adjacent, specific, actionable. |
| Success | Perceptible, then quiet. |

Every data container ships six states; treat them as six different screens.
Independent boolean flags cannot express them: flags admit loading together
with error, cannot distinguish "none exist" from "none match the filter".
Encode as one closed set, so omitting state fails build:

```typescript
| { status: 'loading' }
| { status: 'error'; error: LoadError; retry: () => void }
| { status: 'empty' }                                  // none exist yet
| { status: 'filtered'; clearFilter: () => void }      // none match
| { status: 'partial'; items: Item[]; loadMore: () => void }
| { status: 'ready'; items: Item[] }
```

`empty` and `filtered`: pair most often collapsed into one; they need
different copy and different actions.

## Latency

| Elapsed | Design response |
| --- | --- |
| Under 100ms | Nothing. Show result. |
| 100ms to 400ms | Nothing but result. Loader here flashes, reads as glitch. |
| 400ms to 1s | Local, in-place indication at point of action. |
| 1s to 10s | Determinate progress, rest of interface still usable. |
| Over 10s | Move to background, release user, notify on completion. |

Delay any loader's appearance so fast responses never flash one; once shown,
hold it briefly so it does not flicker out. Skeletons mirror real layout's
dimensions. Optimistic updates apply to reversible actions with honest
rollback and error path; never fake success for something that can fail
permanently.

## Error philosophy

1. **Prevent.** Constrain input so invalid value cannot be entered. Supply
   correct default. Make destructive action non-adjacent to frequent one.
2. **Tolerate.** Parse what user meant. Accept correct but differently
   formatted input, pasted values with spaces, separators, surrounding
   characters. Trim. Correct case.
3. **Recover.** Preserve everything user entered, place message next to
   cause, name fix, move focus to first failure. Reuse information system
   already has.
4. **Explain.** State what happened, what it means, next action, instead of
   exposing raw fault code alone. Technical detail available but secondary.

Never validate on first keystroke, telling user half-typed entry is invalid.

## Destructive actions

* Reversible: perform immediately, offer undo for meaningful window. Faster
  and safer than confirmation, because confirmations are dismissed
  reflexively.
* Irreversible: confirm, naming exact object and exact consequence, verb on
  confirming button. Catastrophic: require deliberate act such as typing
  name.
* Never confirm safe action: it teaches users to dismiss dialogs unread, so
  the one dangerous confirmation gets dismissed too.
* Place destructive actions away from frequent actions and from default
  focused control.

## Feedback placement

* Show progress and results where action was initiated. Toast in far corner
  for action taken in form is message user will not see.
* Toasts only for transient, non-critical confirmations. Anything user must
  act on, or must not miss: inline and persistent.
* Modal never opens modal; give second task a route instead.

## Keyboard and assistive access

* Every pointer action has keyboard path. Everything focusable reachable in
  logical order matching visual order.
* Focus moves into dialog on open, stays within it, returns to trigger on
  close. Escape closes anything dismissible.
* Background content behind modal made inert.
* Keep focused control fully clear of sticky headers, footers, floating
  panels. `a11y` records which part is floor and which is house practice
  above it.
* Provide skip link past repeated navigation.
* Announce asynchronous changes through live region: politely for status,
  assertively only for genuine urgency.
* Any drag interaction has non-drag alternative; dragging unavailable to
  many users.
* Replace any removed outline with focus style at least as visible.
  Suppressed focus is most common accessibility defect.

## Continuity

* URL reflects state: record, tab, filter, sort, page, search.
* Back does what user expects, preserves work.
* Scroll position and expansion state survive navigation and return.
* Drafts persist across refresh and failure.
* Persist preferences: density, dismissed guidance, explicit theme toggle
  where `color` calls for one. Dismissed guidance stays dismissed.
* Preserve authentication flows depending on password managers or paste.
