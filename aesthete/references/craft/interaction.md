# Craft: interaction

The mechanics of an interface that works. The spine carries the kernel; this
is the working detail.

## Principles worth applying correctly

Cite these only where they genuinely apply.

* **Targets**: acquisition difficulty rises as targets get smaller and
  farther away. Frequent actions get large, close targets. Screen edges and
  corners are effectively infinite in depth and are premium real estate.
* **Choices**: decision time rises with the number and complexity of
  options. Reduce, group, order by frequency, and default. Ten equally
  weighted options is a harder screen than three plus a disclosure.
* **Convention**: users form expectations from every other interface they
  use. Departing from convention costs comprehension and must buy something
  real.
* **Conservation of complexity**: the irreducible complexity of a task goes
  somewhere. Put it in the system.
* **Response threshold**: interactions completing within roughly four tenths
  of a second preserve the sense of direct manipulation. Past that the user
  notices waiting and attention starts to drift.
* **Memory**: recognition is cheap, recall is expensive. Show the options.
* **Beauty bias**: attractive interfaces are rated as more usable and their
  problems go unreported. Never accept visual polish as evidence that the
  interaction works.

## The complete state set

Every interactive element:

| State | Requirement |
| --- | --- |
| Rest | Affordance is visible without hover. A control nobody can see is not a control. |
| Hover | Pointer only. Never the sole channel for information or actions. |
| Focus-visible | Always present, never suppressed, high contrast, never clipped or obscured by sticky regions. |
| Active | Immediate acknowledgment at press, before any network work begins. |
| Disabled | Rare, and always explained. Prefer enabled with an explanation on attempt. |
| Loading | In place, with the label preserved so the control does not resize. |
| Error | Adjacent, specific, and actionable. |
| Success | Perceptible, then quiet. |

Every data container adds: loading, empty, filtered-to-empty, partial,
error, populated. These are six different screens, not one screen with a
flag.

## Latency

| Elapsed | Design response |
| --- | --- |
| Under 100ms | Nothing. Show the result. |
| 100ms to 400ms | Nothing but the result. A loader here flashes and reads as a glitch. |
| 400ms to 1s | Local, in-place indication at the point of action. |
| 1s to 10s | Determinate progress, the rest of the interface still usable. |
| Over 10s | Move to background, release the user, notify on completion. |

Delay the appearance of any loader so fast responses never flash one, and
once shown, hold it briefly so it does not flicker out. Skeletons mirror the
real layout's dimensions. Optimistic updates apply to reversible actions
with an honest rollback; never fake success for something that can fail
permanently.

## Error philosophy

1. **Prevent.** Constrain input so the invalid value cannot be entered.
   Supply the correct default. Make the destructive action non-adjacent to
   the frequent one.
2. **Tolerate.** Parse what the user meant. Accept pasted values with
   spaces, separators, and surrounding characters. Trim. Correct case.
   Rejecting a phone number for containing spaces is the system refusing to
   do its job.
3. **Recover.** Preserve everything the user entered, place the message
   next to the cause, name the fix, and move focus to the first failure.
4. **Explain.** Never expose a raw fault code as the whole message. State
   what happened, what it means, and the next action. Keep technical detail
   available but secondary.

Never punish correct-but-differently-formatted input, never clear a form on
failure, and never require re-entering information the system already has.

## Destructive actions

* Reversible: perform it immediately and offer undo for a meaningful window.
  This is faster and safer than a confirmation, because confirmations are
  dismissed reflexively.
* Irreversible: confirm, naming the exact object and the exact consequence,
  with a verb on the confirming button rather than a bare affirmative. For
  the genuinely catastrophic, require a deliberate act such as typing the
  name.
* Never place a destructive action adjacent to a frequent one, and never as
  the default focused control.

## Keyboard and assistive access

* Every pointer action has a keyboard path. Everything focusable is
  reachable in a logical order matching the visual order.
* Focus moves into a dialog on open, stays within it, and returns to the
  trigger on close. Escape closes anything dismissible.
* Background content behind a modal is made inert, not merely visually
  dimmed.
* Focus is never obscured by sticky headers, footers, or floating panels.
* Provide a skip link past repeated navigation.
* Announce asynchronous changes through a live region, politely for status
  and assertively only for genuine urgency.
* Any drag interaction has a non-drag alternative, since dragging is
  unavailable to many users.
* Do not remove the outline without replacing it with something at least as
  visible. Suppressed focus is the single most common accessibility defect.

## Continuity

* URL reflects state: record, tab, filter, sort, page, and search.
* Back does what the user expects and never loses work.
* Scroll position and expansion state survive navigation and return.
* Drafts persist across refresh and failure.
* Preferences persist, including theme choice, density, and dismissed
  guidance. Never re-show something the user dismissed.
* Never require re-entering information already provided, and never break an
  authentication flow that depends on password managers or paste.

## Failure modes

* The happy path shipped alone, so the first real user with slow network or
  empty data sees an unstyled void.
* A spinner for a response that arrives in eighty milliseconds.
* Confirmation dialogs on safe actions, teaching users to dismiss dialogs
  without reading, so the one dangerous confirmation is also dismissed.
* Validation firing on the first keystroke, telling users their half-typed
  entry is invalid.
* Actions revealed only on hover, invisible to touch and keyboard.
* Toasts carrying information the user must act on, in the corner, briefly.
* A modal opened from a modal.

## Completion checks

<validation_checklist>
  <item>Every interactive element ships the full state set; every data container ships all six.</item>
  <item>Latency responses match the budget table, with delayed and minimum-duration loaders.</item>
  <item>Input is parsed liberally and never rejected for formatting the system can normalize.</item>
  <item>Errors preserve entry, sit adjacent to their cause, name the fix, and move focus.</item>
  <item>Reversible destructive actions use undo; irreversible ones name object and consequence.</item>
  <item>Keyboard parity, focus order, focus return, inert backgrounds, and visible focus all hold.</item>
  <item>Every drag has a non-drag alternative and async changes are announced.</item>
  <item>URL, scroll, drafts, and preferences persist; nothing already provided is requested twice.</item>
</validation_checklist>
