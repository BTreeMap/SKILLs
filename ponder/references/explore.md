# Explore: frame, leaves, rounds, stopping

Load when the probe leaves material questions open. Build a frame from the
question and the probe's records, register its leaves, then run rounds until
the stop rules send you to `answer`. Compose the moves below into a frame
around governing mechanisms; most queries mix several modes.

## Moves and the ready frame

Apply each contributing move in table order. Build every frame field before
registering leaves.

| Move | Trigger | Frame field it fills |
| --- | --- | --- |
| `clarify` | Two readings invoke different mechanisms or evidence | One user question, or explicit branches |
| `bind-scope` | The answer changes across context | scope: time, place, jurisdiction, version, population, workload, platform, and stakeholder boundaries that can change the answer |
| `audit-premise` | The query embeds a statistic, history, comparison, or causal claim | premises: every embedded factual or causal claim marked for confirmation or refutation, as a premise leaf that may close `refuted` |
| `split-modes` | Facts, causes, values, interpretations, feasibility, or implementation are mixed | modes: factual, causal, normative, interpretive, feasibility, or implementation claims separated where their evidence and warrants differ |
| `name-mechanisms` | Topic nouns conceal what determines the answer | mechanisms: the laws, incentives, protocols, physical processes, or cost drivers that decide the question |
| `bridge-vocabulary` | The idea may exist under specialist terminology | Search terms and prior-art families |
| `route-evidence` | A claim lacks a natural retrieval target | evidence routes: the expected artifact and source class, per the spine's class table, for each retrievable claim |
| `pose-rival` | The strongest contrary account lives outside the query's own premises | rival: the strongest plausible premise or account that could reverse the emerging answer, with a leaf that may close `refuted` |
| `compile-leaves` | Scope and mechanisms are stable | leaves, below |

For critical ambiguity, ask one focused question. If clarification is
unavailable, branch each plausible reading and use the branch point as
Boundary material. Re-run `clarify` when evidence exposes a new
interpretation.

## Leaves

Turn open work into independent questions, each settled by one retrieval
act. Decompose by governing principle: each leaf names a mechanism and a
retrievable claim, and the leaves group by mechanism.

- Put dependent sub-questions in the draft's `[~]` chain, so ledger leaves
  and fan-out stay independent.
- 3 to 10 leaves covers the worked range. Past 10, fold near-duplicates
  before searching; below 3 still works.
- Register leaves as `leaves` entries in the round's `note` batch: keywords,
  question, origin. Reference them by the identifiers the output echoes.

## Worked frames

<examples for="framing">

<example for="comparative-performance">
<context for="query">How could IEEE 754 non-associativity make a Rust dot product eight times slower than C++?</context>
<variant for="moves">audit-premise, bind-scope, split-modes, name-mechanisms, route-evidence</variant>
<variant for="leaves">Reproduce the eightfold benchmark with source, Rust and C++ versions, compiler flags, hardware; separate IEEE 754 arithmetic from each language's optimization contract; compare vectorization, reduction order, aliasing, generated assembly; locate the fast-math or explicit-SIMD boundary where the result changes.</variant>
</example>

<example for="shared-credential-writes">
<context for="query">Would a broker process serializing access fix a shared credentials file that concurrent sessions keep corrupting?</context>
<variant for="moves">audit-premise, pose-rival, name-mechanisms, split-modes, route-evidence</variant>
<variant for="leaves">Test the premise that interleaved writes cause the corruption; retrieve the rival account where single-use refresh-token rotation invalidates a stored grant; compare file locking, atomic replace, and broker serialization against the interval that needs exclusion; locate the platform's documented credential-helper seam.</variant>
</example>

<example for="comparative-public-recording">
<context for="query">Where do major jurisdictions draw the legal boundaries for noncommercial filming in public places?</context>
<variant for="moves">clarify, bind-scope, split-modes, route-evidence, compile-leaves</variant>
<variant for="leaves">Choose representative jurisdictions; separate public property from privately controlled public space; retrieve rules on permits, privacy, personality rights, data protection, sound recording, later publication; distinguish noncommercial purpose from conduct regulated regardless of profit.</variant>
</example>

<example for="petition-timing">
<context for="query">Is a ten-business-day filing delay on a work petition worth trading for a conference trip before a fixed start date?</context>
<variant for="moves">audit-premise, split-modes, bind-scope, name-mechanisms</variant>
<variant for="leaves">Confirm the premium adjudication clock, what pauses it, and what the receipt date sets; surface the buried variable, since travel while a change-of-status petition is pending reads as abandonment; bind filing type, current status, consular versus in-country processing; name where licensed judgment is required without letting that replace retrieval.</variant>
</example>

<example for="distributed-network-failures">
<context for="query">Beyond incast and microbursts, what degraded network conditions affect modern ML training clusters?</context>
<variant for="moves">bind-scope, name-mechanisms, bridge-vocabulary, route-evidence</variant>
<variant for="leaves">Partition by synchronized traffic, congestion-control response, lossless-fabric feedback, load imbalance, ordering and retransmission, host or NIC stalls, collective stragglers; retrieve measured signatures and mitigations per mechanism.</variant>
</example>

<example for="research-crowdfunding">
<context for="query">Can crowdfunding fund a research lab, what predicts campaign success, and where does the money legally land?</context>
<variant for="moves">split-modes, name-mechanisms, route-evidence, compile-leaves</variant>
<variant for="leaves">Retrieve measured campaign samples for predictors, holding existing audience apart from platform choice; route the destination and tax-receipt question to constitutive platform and university policy; close donation framing unresolved where the literature is silent instead of borrowing an adjacent nonprofit result.</variant>
</example>

<example for="tunneled-path-latency">
<context for="query">How much latency does tunneling a service through a third region add over a direct path, and what decides the increase?</context>
<variant for="moves">bind-scope, name-mechanisms, route-evidence, split-modes</variant>
<variant for="leaves">Bind endpoints, tunnel type, provider; decompose the increase into physical path length, peering and transit choice, encapsulation and encryption cost, queueing under load; retrieve looking-glass and probe measurements; report a range rather than one figure.</variant>
</example>

<example for="moving-reflector">
<context for="query">Could a curved mirror making small millisecond-scale motions improve wireless signal coverage?</context>
<variant for="moves">clarify, name-mechanisms, bridge-vocabulary</variant>
<variant for="leaves">Clarify whether the mirror rotates, orbits, or oscillates, and which radio band it redirects; retrieve wavelength-to-curvature limits, actuator response, coherence and fading effects, reconfigurable-reflector prior art.</variant>
</example>

<example for="downtown-parking">
<context for="query">Which garage near a downtown restaurant is the best value for an evening?</context>
<variant for="moves">bind-scope, route-evidence, audit-premise, split-modes</variant>
<variant for="leaves">Take operator rate pages as constitutive on price; treat review aggregators as reported on access and safety; bind evening hours, event surcharges, walking distance; reconcile published capacity against the operator's own notice of reduced spaces.</variant>
</example>

<example for="urban-redevelopment">
<context for="query">Why might a city fear gentrification despite possible gains in amenities and tax revenue?</context>
<variant for="moves">audit-premise, split-modes, bind-scope, name-mechanisms</variant>
<variant for="leaves">Separate aggregate amenities and revenue from who receives them; test displacement, tenure, tax-base, service, fiscal-timing mechanisms; separate causal evidence from the normative weighting across incumbent residents, newcomers, owners, renters, city government.</variant>
</example>

<example for="modern-adaptation">
<context for="query">How does a recent film adaptation of an ancient epic reinterpret it for a modern audience?</context>
<variant for="moves">bind-scope, audit-premise, split-modes, route-evidence</variant>
<variant for="leaves">Establish the released version; compare structure and characters against the source; separate visible choices, attested intent, critical interpretation; attribute intent through interviews.</variant>
</example>

<example for="aversive-habit-devices">
<context for="query">Do self-administered aversive stimuli such as shock wristbands or snapped rubber bands break habits?</context>
<variant for="moves">bind-scope, split-modes, name-mechanisms, route-evidence</variant>
<variant for="leaves">Separate clinical aversion therapy and its abandonment from consumer devices; read vendor material as attested about the product and silent on efficacy; corroborate thin trials before stating plainly; carry the absent controlled evaluation into Open.</variant>
</example>

<example for="tests-and-proof">
<context for="query">Can tests and code agree while both violate the intended specification, and can formal proofs prevent this?</context>
<variant for="moves">split-modes, name-mechanisms, bridge-vocabulary, compile-leaves</variant>
<variant for="leaves">Separate specification choice from implementation conformance; compare contracts, property testing, refinement and dependent types, theorem proving, model checking; name each guarantee and trusted base; keep specification error and common-mode generation failure as boundaries.</variant>
</example>

<example for="agent-ensemble-benefit">
<context for="query">Do multi-agent ensembles beat one strong model at matched compute?</context>
<variant for="moves">audit-premise, bind-scope, pose-rival, route-evidence</variant>
<variant for="leaves">Bind task family, compute accounting, evaluation; retrieve published results on both sides; separate framework marketing from measured matched-compute comparison; expect real survivors from the sweep.</variant>
</example>

<example for="experiment-vocabulary">
<context for="query">Is a three-arm within-subjects study an A/B test, and what makes a design a bandit instead?</context>
<variant for="moves">clarify, bridge-vocabulary, split-modes, route-evidence</variant>
<variant for="leaves">Retrieve constitutive definitions from method texts and venue conventions; separate naming convention from statistical design; identify adaptive allocation as the property that turns arms into a bandit.</variant>
</example>

<example for="work-visa-routes">
<context for="query">Which visa routes admit a researcher to a US university post, read both literally and as the underlying goal?</context>
<variant for="moves">clarify, bind-scope, split-modes, route-evidence, compile-leaves</variant>
<variant for="leaves">Branch the stated reading and the likelier goal, then answer both; give each route one leaf; bind nationality, employer type, cap exemption, timing; close rules under active litigation as unresolved.</variant>
</example>

<example for="hardware-search-tree">
<context for="query">How can a splay tree be implemented for modern hardware with low constant overhead?</context>
<variant for="moves">clarify, bind-scope, name-mechanisms, bridge-vocabulary</variant>
<variant for="leaves">Bind CPU, GPU, FPGA, or ASIC and the operation mix; account for pointer chasing, branches, rotations, cache locality, write traffic, concurrency; compare top-down splaying, index-based layouts, batching, alternative search structures before optimizing splay itself.</variant>
</example>

<example for="local-model-fit">
<context for="query">Which local language models run usefully in 6 GB of GPU memory, and does a 24 GB CPU-only server do better?</context>
<variant for="moves">bind-scope, name-mechanisms, split-modes, route-evidence</variant>
<variant for="leaves">Separate quantized weight size from KV-cache growth with context; name the binding resource per machine, capacity on the GPU and memory bandwidth on the CPU; retrieve measured throughput per backend; state usable memory rather than nominal.</variant>
</example>

<example for="delegated-credentials">
<context for="query">Why are access tokens centrally issued, and could client-signed requests backed by 7-day certificates and CRLs replace them?</context>
<variant for="moves">audit-premise, bind-scope, name-mechanisms, bridge-vocabulary, compile-leaves</variant>
<variant for="leaves">Separate centralized token issuance from centralized authorization; establish the threat model and client key storage; compare bearer tokens, mutual TLS, proof-of-possession, delegated credentials; analyze 7-day certificate and CRL freshness, replay, logout, authorization change, rotation, privacy, operational cost.</variant>
</example>

<example for="feature-trust-boundary">
<context for="query">What does a remote-control feature do, how is it enabled, and what trust boundary does it create?</context>
<variant for="moves">split-modes, name-mechanisms, route-evidence</variant>
<variant for="leaves">Retrieve the definition and toggle path from attested documentation; retrieve the stated permissions and data flow; assign the trust boundary to the derived chain, since it composes those facts rather than sitting in any document.</variant>
</example>

<example for="representation-brokers">
<context for="query">Which agencies represent academics for press and speaking work, and how does the money differ between them?</context>
<variant for="moves">bind-scope, route-evidence, split-modes</variant>
<variant for="leaves">Retrieve rosters and service descriptions as reported sources; separate retainer, commission, fee-split structures; hedge each claim to its source; leave individual staff contacts unresolved, since rosters go stale and no artifact supports them.</variant>
</example>

<example for="index-fund-timing">
<context for="query">Is a broad-market equity index fund a good buy during a period of geopolitical disruption?</context>
<variant for="moves">clarify, audit-premise, split-modes, name-mechanisms</variant>
<variant for="leaves">Resolve what good buy means: horizon, alternative use of the money, tolerance for drawdown; test the premise that the disruption is not already priced; retrieve fund composition, fees, measured drawdown-and-recovery history; keep future return unretrievable and say so.</variant>
</example>

<example for="multi-party-threads">
<context for="query">How can several people hold one thread with an assistant across the major vendors, in real time or asynchronously?</context>
<variant for="moves">bind-scope, split-modes, route-evidence, compile-leaves</variant>
<variant for="leaves">Give each vendor independent leaves; separate shared threads from workspace sharing, link sharing, export; bind plan tier, admin policy, regional rollout; hedge staged availability.</variant>
</example>
</examples>

## Frame checks

Before bundling the leaves, verify:

<checklist>
  <item>Every critical ambiguous term is resolved or branched.</item>
  <item>Every embedded premise supports a `refuted` close while the frame remains valid, and the frame names evidence that could refute it.</item>
  <item>Factual, causal, normative, interpretive, feasibility, and implementation claims use distinct warrants where needed.</item>
  <item>Every leaf names one governing mechanism and one plausible evidence route.</item>
  <item>Leaves are independent, jointly cover the material question, and use mechanism-level names.</item>
  <item>The rival premise and answer-flipping boundaries are explicit.</item>
</checklist>

## Bundle and delegate

Delegation starts here, after round one; the lead retains the comprehensive
view. Partition open leaves into disjoint bundles by corpus, vocabulary, or
principle; jointly cover the open set. Prefer fewer, fuller bundles.

Delegate through `/summon fanout`, one delegate per bundle, with the brief
`brief` lays out. Summon's mode table decides when a bundle runs inline
instead; the ledger state is the same either way, and delegate identity
stays outside it.

Delegates read source pages and return closure proposals; they write
nothing. The lead judges each return under summon's review and checks
inflated source-class tags against the class table in the spine.

## Admit a round

1. Deduplicate sources.
2. Judge each close. Use anomalous evidence to test the frame. Before a
   `retrieved` close, name its falsifier. Close contradicted premises as
   `refuted`; they feed Rival. Close deliberately abandoned leaves as
   `unresolved` with reason `not_pursued` and its explanation.
3. Adapt the leaf set: add delegate discoveries as `"origin": "spawned"` and
   retire superseded leaves.
4. Admit spawned leaves, sources, closes, and a `checkpoints` entry as one
   `note` batch. The checkpoint carries the round's declared search count
   (the sum of delegates' `searches_spent`); the same output returns the
   updated yield table. On rejection, apply every listed fix and resend
   once.

## Stop or continue

Falling yield prompts a reframe-or-stop decision. Apply these bounds:

- Two unproductive rounds: stop, close remaining open leaves as
  `unresolved`, and draft. One authoritative source can complete a
  productive round.
- Begin saturation judgment one round past the declared focus.
- Run one to three rounds. A fourth-round need triggers reframing and
  folding.
