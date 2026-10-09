# Surface: product

Application UI, dashboards, tables, forms, wizards, settings, consoles. The
user arrives with intent and often returns daily. The job is throughput and
confidence: complete the task quickly, know the state, never lose work.

Product surfaces optimize the thousandth use, not a first impression. Budget
delight against repetition: an animation a user sees a thousand times stays
under the latency budget like anything else.

## Governing posture

* **Familiarity beats invention.** Users spend most of their time in other
  applications. Place things where they are placed elsewhere; spend novelty
  on the domain-specific parts nobody else has solved.
* **Density is a service.** Experts want more on screen. Achieve density
  with alignment, tabular numerals, and hairlines; keep type at comfortable
  reading sizes.
* **Default to the safe, reversible, and common.** The most frequent action
  is one click away.
* **State is visible.** At any moment the user can answer: where am I, what
  is selected, what is happening, what changed, and what can I do next.

## Navigation and structure

* Use one primary navigation model, chosen for the depth of the product: a
  sidebar for many peer sections, a top bar for few, tabs only for switching
  views of one object.
* Current location is unambiguous in the navigation, and the page title
  matches the navigation label exactly.
* Everything the user can reach is linkable and survives a refresh.
* Depth over three levels needs a different structure.

## Forms

* Put a visible label above the field. Placeholder text disappears exactly
  when it is needed and fails contrast and recall.
* Use one column; multi-column forms cause field skipping. Group related
  fields into sections with headings instead.
* Ask for the minimum. Every field justifies itself against the primary
  goal, and anything derivable is derived.
* Parse phone numbers, dates, currency, identifiers, and pasted values with
  spaces or separators; formatting is the system's job.
* Validate on blur for a completed field, on submit for the whole form, and
  after the user finishes typing. Once a field has errored, revalidate as
  they type so the error clears live.
* On a long form, a summary at the top links to each failure.
* Mark required or optional explicitly, whichever is rarer.

## Tables and data

* Show what the user decides with; move the rest behind a detail view or a
  column picker.
* Align text left and numbers right, with numbers in tabular figures so
  digits form columns.
* The header row stays visible while scrolling. Row identity stays visible
  while scrolling horizontally.
* Sorting, filtering, and pagination state persist across return visits.
* Selection shows a persistent count and the actions that apply to it, and
  bulk destructive actions confirm with the exact count.

## Dashboards

* State one question per view in the title before adding charts. Choose each
  chart's form for that question, a decision separate from its palette
  (`color`).
* Rank by decision value. The number that changes behavior goes top-left in
  left-to-right reading orders.
* Every metric carries its comparison: a number without a baseline, target,
  or trend cannot be acted on.
* Say when the data is from, and whether it is live, cached, or partial.

## Modals and disclosure

* A modal interrupts. Use it only when the task must be completed or
  abandoned before anything else continues. Everything else is inline
  expansion, a side panel, or its own route.
* Disclose progressively by frequency: common controls visible, advanced
  controls behind a labeled expansion, dangerous controls further still.

## Empty states

Say what belongs here and why it is worth having, and offer the single
action that populates it. Distinguish never-had-any from
none-match-this-filter from you-cleared-them-all: each needs its own copy
and action, and the filtered one offers to clear the filter.
