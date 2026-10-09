# Surface: product

Application UI, dashboards, tables, forms, wizards, settings, consoles. User
arrives with intent, often returns daily. Job: throughput and confidence:
complete task quickly, know state, never lose work.

Product surfaces optimize thousandth use, not first impression. Budget
delight against repetition: animation user sees a thousand times stays under
latency budget like anything else.

## Governing posture

* **Familiarity beats invention.** Users spend most time in other
  applications. Place things where they are placed elsewhere; spend novelty
  on domain-specific parts nobody else has solved.
* **Density is a service.** Experts want more on screen. Achieve density
  with alignment, tabular numerals, hairlines; keep type at comfortable
  reading sizes.
* **Default to safe, reversible, common.** Most frequent action one click
  away.
* **State visible.** At any moment user can answer: where am I, what is
  selected, what is happening, what changed, what can I do next.

## Navigation and structure

* One primary navigation model, chosen for product's depth: sidebar for many
  peer sections, top bar for few, tabs only for switching views of one
  object.
* Current location unambiguous in navigation; page title matches navigation
  label exactly.
* Everything user can reach is linkable, survives refresh.
* Depth over three levels needs different structure.

## Forms

* Visible label above field. Placeholder text disappears exactly when
  needed, fails contrast and recall.
* One column; multi-column forms cause field skipping. Group related fields
  into sections with headings instead.
* Ask for minimum. Every field justifies itself against primary goal;
  anything derivable is derived.
* Parse phone numbers, dates, currency, identifiers, pasted values with
  spaces or separators; formatting is system's job.
* Validate on blur for completed field, on submit for whole form, after user
  finishes typing. Field has errored: revalidate as they type so error
  clears live.
* Long form: summary at top links to each failure.
* Mark required or optional explicitly, whichever is rarer.

## Tables and data

* Show what user decides with; rest behind detail view or column picker.
* Text left, numbers right, numbers in tabular figures so digits form
  columns.
* Header row visible while scrolling. Row identity visible while scrolling
  horizontally.
* Sorting, filtering, pagination state persist across return visits.
* Selection shows persistent count and actions that apply to it; bulk
  destructive actions confirm with exact count.

## Dashboards

* State one question per view in title before adding charts. Choose each
  chart's form for that question, decision separate from its palette
  (`color`).
* Rank by decision value. Number that changes behavior goes top-left in
  left-to-right reading orders.
* Every metric carries comparison: number without baseline, target, or trend
  cannot be acted on.
* Say when data is from; live, cached, or partial.

## Modals and disclosure

* Modal interrupts. Use only when task must be completed or abandoned before
  anything else continues. Everything else: inline expansion, side panel, or
  own route.
* Disclose progressively by frequency: common controls visible, advanced
  behind labeled expansion, dangerous further still.

## Empty states

Say what belongs here and why worth having; offer single action that
populates it. Distinguish never-had-any from none-match-this-filter from
you-cleared-them-all: each needs own copy and action; filtered one offers to
clear filter.
