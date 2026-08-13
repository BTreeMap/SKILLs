# Surface: product

Application UI, dashboards, tables, forms, wizards, settings, consoles. The
user arrives with intent and often returns daily. The job is throughput and
confidence: complete the task quickly, know the state, never lose work.

Marketing surfaces optimize a first impression. Product surfaces optimize
the thousandth use. Budget delight against repetition: an animation a user
sees a thousand times has to stay under the latency budget like anything else.

## Governing posture

* **Familiarity beats invention.** Users spend most of their time in other
  applications. Place things where they are placed elsewhere; spend novelty
  budget on the domain-specific parts nobody else has solved.
* **Density is a service, not a compromise.** Experts want more on screen.
  Achieve density with alignment, tabular numerals, and hairlines rather
  than with shrinking type below comfortable reading sizes.
* **Default to the safe, reversible, and common.** The most frequent action
  is one click away; the destructive one is not adjacent to it.
* **State is visible.** At any moment the user can answer: where am I, what
  is selected, what is happening, what changed, and what can I do next.

## Navigation and structure

* Use one primary navigation model, chosen for the depth of the product: a
  sidebar for many peer sections, a top bar for few, tabs only for switching
  views of one object.
* Current location is unambiguous in the navigation, and the page title
  matches the navigation label exactly. Different names for the same place
  is the cheapest possible confusion to avoid.
* The URL encodes real state: the record, the tab, the filters, the page.
  Everything the user can reach should be linkable and survive a refresh.
* Depth over three levels needs a different structure, not a third nested
  menu.

## Forms

* Put a visible label above the field. Placeholder text disappears exactly
  when it is needed and fails contrast and recall.
* One column. Multi-column forms cause field skipping. Group related fields
  into sections with headings instead.
* Ask for the minimum. Every field justifies itself against the primary
  goal, and anything derivable is derived rather than requested.
* Be liberal in what you accept. Parse phone numbers, dates, currency,
  identifiers, and pasted values with spaces or separators instead of
  rejecting them. Formatting is the system's job.
* Validate at the right moment: on blur for a completed field, on submit for
  the whole, and after the user finishes typing rather than on every
  keystroke. Once a field has errored, revalidate as they type so the error
  clears live.
* Errors sit adjacent to the field, name the problem and the fix, and move
  focus to the first failure. A summary at the top of a long form links to
  each failure.
* Required and optional are marked explicitly, whichever is rarer.
* Preserve entry across navigation, refresh, and failure. Losing a completed
  form to a server error is the most damaging single failure a form has.
* Disable a submit button only when disabled state is explained. Preferably
  leave it enabled and explain what is missing on click.

## Tables and data

* Column choice is the design. Show what the user decides with; move the
  rest behind a detail view or a column picker.
* Align text left, numbers right, and set numbers in tabular figures so
  digits form columns.
* The header row stays visible while scrolling. Row identity stays visible
  while scrolling horizontally.
* Sorting, filtering, and pagination state live in the URL and persist
  across return visits.
* Row actions are discoverable without hover, since hover does not exist on
  touch and is invisible to keyboard users.
* Selection shows a persistent count and the actions that apply to it, and
  bulk destructive actions confirm with the exact count.
* Virtualize long tables while preserving find-in-page and keyboard
  navigation, or provide an explicit alternative.
* Every table ships the full container state set. The never-had-any and
  none-match-the-filter states are the pair most often conflated; the second
  must offer to clear the filter.

## Dashboards

* State one question per view in the title before adding charts.
* Rank by decision value, not by data availability. The number that changes
  behavior goes top-left in left-to-right reading orders.
* Every metric carries its comparison. A number without a baseline, target,
  or trend cannot be acted on.
* Say when the data is from, and whether it is live, cached, or partial.
* Never fabricate sample data that could be mistaken for real. Label
  illustrative data unmistakably.
* Choosing a chart form and its palette is a separate craft decision; return
  to the spine to load the color reference when it comes up.

## Modals, dialogs, and disclosure

* A modal interrupts. Use it only when the task must be completed or
  abandoned before anything else continues. Everything else is inline
  expansion, a side panel, or its own route.
* A modal that opens a modal needs a route instead.
* Every dialog: focus moves in on open, is trapped while open, returns to
  the trigger on close, and escape closes.
* Confirmation dialogs name the exact object and the exact consequence, and
  the confirming button is a verb naming the action rather than a bare
  affirmative.
* Progressive disclosure by frequency: common controls visible, advanced
  controls behind a labeled expansion, dangerous controls further still.

## Feedback and system state

* Every action produces a perceptible result within the response budget.
  Silence after a click is the most common cause of duplicate submissions.
* Show progress where the action was initiated. A toast in the far corner
  for an action taken in a form is a message the user will not see.
* Reserve toasts for transient, non-critical confirmations. Anything the
  user must act on, or must not miss, belongs inline and persistent.
* Optimistic updates apply to reversible actions with a clear rollback and
  an honest error path. Never fake success for something that can fail
  permanently.
* Preserve scroll position and expansion state across navigation and return.

## Empty states

The empty state is the first thing most users see and the least designed
screen in most products. Say what belongs here, why it is worth having, and
offer the single action that populates it. Distinguish
never-had-any from none-match-this-filter from you-cleared-them-all: they need
different copy and different actions.
