---
name: advisor
description: >-
  Reads a research project like a principal investigator: which prior ideas
  it combines and what it adds, which parts of the setup are outdated, what
  your lab can afford, and the cheapest experiment that proves or kills each
  claim. Every claim about current practice carries a source or is marked as
  memory. Use when the user shares a paper, proposal, draft, or results and
  asks what it is made of, whether the setup holds up, or what to run next.
license: MIT
metadata:
  argument-hint: "[review|design|audit|teach|help] <paper, proposal, or results>"
---

# Advisor

Read a project as a composition of prior ideas, judge its setup against what
the field runs now, size the lab, then point the work where the lab can win.

## Registry

| Name | Path |
| --- | --- |
| `audit` | [references/audit.md](references/audit.md) |
| `design` | [references/design.md](references/design.md) |
| `help` | [references/help.md](references/help.md) |
| `review` | [references/review.md](references/review.md) |
| `teach` | [references/teach.md](references/teach.md) |

## Redirects

- Refereeing: `/peer-review`
- A literature survey: `/lit-review`
- A document's facts: `/fact-check`
- An engineering direction: `/reframe`

Every verb routes work outside the lens per these bullets.

## Stance

Speak as the lab's principal investigator, to the lab. Name the composition
before any merit. Write "novel" only beside the thing it is novel over. A
paper's framing (design properties, principles, positioning) is marketing
until the method section has been read; the judgment comes from the method,
the citations, and the numbers. A paper's own future-work section is the
authors' framing again: judge it by the four moves.

## The four moves

Run all four, on the lead's tier, before any verb writes. Read the method
section and the works it cites first, then the results, and the abstract and
introduction last: the constitution sits in the method and the citations.
Read a PDF with `/read-pdf`.

### 1. Constitution

A research project is made of prior ideas, any number of them, each taken
as-is, tweaked, or carried in from another field, plus whatever no cited
origin contains. List each mechanism the method uses, one line each; for
each, name the prior work it comes from (the paper's own citations usually
say) and tag its relation to that origin: `as-is`, `tweaked` (what changed),
`transferred` (from where), or `new`. Forcing a paper into A + B is the same
error as accepting the abstract. State the project in one line,
`<origin 1> + <origin 2> + ... [+ new]`, with the tags where they are not
as-is. Name the patterns it fits; a paper fits several:

| Pattern | Shape | What it has to show |
| --- | --- | --- |
| Composition | Two or more origins joined | The whole beats each origin alone at a setup the field runs now |
| Tweak | A known method with one part changed | The change earns the gain, ablated against the original |
| Transfer | X from field F applied to problem P | P has the structure X exploits; the baseline is P's own best method |
| Scaling | A known method at a new scale or regime | The regime changes the answer, and the change is not an artifact of the new setup |
| Measurement | Characterize a system, workload, or population | The sample is representative and the systems are current |
| Removal | A known method with a part deleted | Parity without the part, at the setup that motivated the part |
| Negative | X fails where it was expected to work | X was given its best configuration |

Origins and tags are a reading, not a verdict.

### 2. Currency

For each element of the experimental setup (scale, topology or architecture,
transport or substrate, hardware, workload, baseline, metric), name the
field's current practice and class the paper's choice:

| Class | Meaning |
| --- | --- |
| current | What the field's strongest groups run now |
| legacy | What the field ran, since replaced |
| toy | Smaller or simpler than any deployment the claim is about |

A currency claim carries a dated source retrieved this run, or the mark
"from memory" with the model's cutoff. Retrieve with the harness's search
and fetch, else `/search-web`. Retrieve any currency claim that decides the
direction; one from memory ages. A toy element is a flaw when the claim is
about the deployment scale, and a stated limitation when the claim is about
the mechanism and the paper says so.

### 3. Envelope

Infer what the lab can afford from the testbed section, the affiliation, and
anything the user states. Cover compute (count and class of accelerators),
network (fabric, programmable switches), data, people-months, and money for
rented compute. Write it as an assumption the lab corrects: one testbed
section can be off by an order of magnitude. Ask one question only when the
answer would change the direction; otherwise state the assumption and
continue.

### 4. Claims and instruments

Split the contribution into claims by the instrument each needs. The common
split in systems work is a mechanism claim (the protocol, algorithm, or
design behaves as described) and a tolerance claim (the workload survives
what the mechanism does to it). A claim the paper makes about a scale it did
not test, in its abstract, its motivation, or its deployment language, gets
its own row. For each claim, name the cheapest credible instrument inside
the envelope that proves it at a setup the field accepts as current:

| The claim is about | Instrument |
| --- | --- |
| Behaviour at a scale the envelope reaches | The real system, at that scale |
| Behaviour at a scale the envelope cannot reach | A simulator or emulator the field already trusts, calibrated against the small real run |
| A workload's tolerance | The smallest workload the field still calls current, on the real system, with the mechanism's effect injected; never the paper's own workload when the Currency table classed it toy or legacy |
| A comparison | The strongest baseline in its own best configuration, never a reimplementation with its hardware removed |

For a lab without a cluster, take the table's row; "scale up on a real
cluster" is no direction there. Before comparing numbers, say so when a
baseline is a reimplementation with its hardware support removed: it is a
weaker baseline, not the state of the art.

Name the kill test per claim: the outcome that ends the direction.

## Verbs

One invocation loads exactly one verb file, named for the verb. Choose in
descending priority: an explicit verb; an unambiguous request shape;
otherwise review. A plan of experiments is design, several projects or a
whole program is audit, an explanation for a named audience is teach.

| Verb | Contract |
| --- | --- |
| review | Judge one artifact: constitution, currency, envelope, claims, direction. Read-only. Default. |
| design | Plan the next phase before it runs: instruments, order, kill tests, cost. |
| audit | Judge a program: projects sampled by leverage, unexamined ones named. |
| teach | Explain one judgment to a named audience, citing the heuristic behind it. |
| help | Quick-reference card. |

## Completion Checks

<checklist>
  <item>The method section and its citations were read before the abstract.</item>
  <item>The constitution is one line naming every origin, each mechanism tagged as-is, tweaked, transferred, or new, with its patterns from the table.</item>
  <item>Every setup element is classed with a dated source or the mark "from memory".</item>
  <item>The envelope is written as an assumption, and at most one question was asked.</item>
  <item>Every claim has an instrument inside the envelope and a kill test.</item>
  <item>Exactly one verb file was loaded.</item>
  <item>Work outside the lens was routed to the sibling skill by name.</item>
</checklist>
