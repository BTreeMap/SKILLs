# Explore: frame, leaves, cycles, stopping

Load when probe leaves material questions open. Build frame from question
and probe's records, register its leaves, then run cycles until stop rules
send you to `answer`. Compose moves below into frame around governing
mechanisms; most queries mix several modes.

## Moves and the ready frame

Apply each contributing move in table order. Build every frame field before
registering leaves.

| Move | Trigger | Frame field it fills |
| --- | --- | --- |
| `clarify` | Two readings invoke different mechanisms or evidence | One user question, or explicit branches |
| `bind-scope` | Answer changes across context | scope: time, place, jurisdiction, version, population, workload, platform, stakeholder boundaries that can change answer |
| `audit-premise` | Query embeds statistic, history, comparison, or causal claim | premises: every embedded factual or causal claim marked for confirmation or refutation, as premise leaf that may close `refuted` |
| `split-modes` | Facts, causes, values, interpretations, feasibility, or implementation mixed | modes: factual, causal, normative, interpretive, feasibility, or implementation claims separated where their evidence and warrants differ |
| `name-mechanisms` | Topic nouns conceal what determines answer | mechanisms: laws, incentives, protocols, physical processes, or cost drivers deciding question |
| `bridge-vocabulary` | Idea may exist under specialist terminology | Search terms and prior-art families |
| `route-evidence` | Claim lacks natural retrieval target | evidence routes: expected artifact and source class, per spine's class table, for each retrievable claim |
| `pose-rival` | Strongest contrary account lives outside query's own premises | rival: strongest plausible premise or account that could reverse emerging answer, with leaf that may close `refuted` |
| `compile-leaves` | Scope and mechanisms stable | leaves, below |

Critical ambiguity: ask one focused question. Clarification unavailable:
branch each plausible reading, use branch point as Boundary material. Re-run
`clarify` when evidence exposes new interpretation.

## Leaves

Turn open work into independent questions, each settled by one retrieval
act. Decompose by governing principle: each leaf names mechanism and
retrievable claim; leaves group by mechanism.

- Put dependent sub-questions in draft's `[~]` chain, so ledger leaves and
  groups stay independent.
- 3 to 10 leaves covers worked range. Past 10, fold near-duplicates before
  searching; below 3 still works.
- Register leaves as `leaves` entries in cycle's `record` batch: keywords,
  question, origin. Reference them by identifiers output echoes.

## Worked frames

**Example: comparative-performance**

Query: How could IEEE 754 non-associativity make a Rust dot product eight
times slower than C++?

Moves: audit-premise, bind-scope, split-modes, name-mechanisms,
route-evidence

Leaves: Reproduce the eightfold benchmark with source, Rust and C++
versions, compiler flags, hardware; separate IEEE 754 arithmetic from each
language's optimization contract; compare vectorization, reduction order,
aliasing, generated assembly; locate the fast-math or explicit-SIMD boundary
where the result changes.

**Example: shared-credential-writes**

Query: Would a broker process serializing access fix a shared credentials
file that concurrent sessions keep corrupting?

Moves: audit-premise, pose-rival, name-mechanisms, split-modes,
route-evidence

Leaves: Test the premise that interleaved writes cause the corruption;
retrieve the rival account where single-use refresh-token rotation
invalidates a stored grant; compare file locking, atomic replace, and broker
serialization against the interval that needs exclusion; locate the
platform's documented credential-helper seam.

**Example: comparative-public-recording**

Query: Where do major jurisdictions draw the legal boundaries for
noncommercial filming in public places?

Moves: clarify, bind-scope, split-modes, route-evidence, compile-leaves

Leaves: Choose representative jurisdictions; separate public property from
privately controlled public space; retrieve rules on permits, privacy,
personality rights, data protection, sound recording, later publication;
distinguish noncommercial purpose from conduct regulated regardless of
profit.

**Example: petition-timing**

Query: Is a ten-business-day filing delay on a work petition worth trading
for a conference trip before a fixed start date?

Moves: audit-premise, split-modes, bind-scope, name-mechanisms

Leaves: Confirm the premium adjudication clock, what pauses it, and what the
receipt date sets; surface the buried variable, since travel while a
change-of-status petition is pending reads as abandonment; bind filing type,
current status, consular versus in-country processing; name where licensed
judgment is required without letting that replace retrieval.

**Example: distributed-network-failures**

Query: Beyond incast and microbursts, what degraded network conditions
affect modern ML training clusters?

Moves: bind-scope, name-mechanisms, bridge-vocabulary, route-evidence

Leaves: Partition by synchronized traffic, congestion-control response,
lossless-fabric feedback, load imbalance, ordering and retransmission, host
or NIC stalls, collective stragglers; retrieve measured signatures and
mitigations per mechanism.

**Example: research-crowdfunding**

Query: Can crowdfunding fund a research lab, what predicts campaign success,
and where does the money legally land?

Moves: split-modes, name-mechanisms, route-evidence, compile-leaves

Leaves: Retrieve measured campaign samples for predictors, holding existing
audience apart from platform choice; route the destination and tax-receipt
question to constitutive platform and university policy; close donation
framing unresolved where the literature is silent instead of borrowing an
adjacent nonprofit result.

**Example: tunneled-path-latency**

Query: How much latency does tunneling a service through a third region add
over a direct path, and what decides the increase?

Moves: bind-scope, name-mechanisms, route-evidence, split-modes

Leaves: Bind endpoints, tunnel type, provider; decompose the increase into
physical path length, peering and transit choice, encapsulation and
encryption cost, queueing under load; retrieve looking-glass and probe
measurements; report a range rather than one figure.

**Example: moving-reflector**

Query: Could a curved mirror making small millisecond-scale motions improve
wireless signal coverage?

Moves: clarify, name-mechanisms, bridge-vocabulary

Leaves: Clarify whether the mirror rotates, orbits, or oscillates, and which
radio band it redirects; retrieve wavelength-to-curvature limits, actuator
response, coherence and fading effects, reconfigurable-reflector prior art.

**Example: downtown-parking**

Query: Which garage near a downtown restaurant is the best value for an
evening?

Moves: bind-scope, route-evidence, audit-premise, split-modes

Leaves: Take operator rate pages as constitutive on price; treat review
aggregators as reported on access and safety; bind evening hours, event
surcharges, walking distance; reconcile published capacity against the
operator's own notice of reduced spaces.

**Example: urban-redevelopment**

Query: Why might a city fear gentrification despite possible gains in
amenities and tax revenue?

Moves: audit-premise, split-modes, bind-scope, name-mechanisms

Leaves: Separate aggregate amenities and revenue from who receives them;
test displacement, tenure, tax-base, service, fiscal-timing mechanisms;
separate causal evidence from the normative weighting across incumbent
residents, newcomers, owners, renters, city government.

**Example: modern-adaptation**

Query: How does a recent film adaptation of an ancient epic reinterpret it
for a modern audience?

Moves: bind-scope, audit-premise, split-modes, route-evidence

Leaves: Establish the released version; compare structure and characters
against the source; separate visible choices, attested intent, critical
interpretation; attribute intent through interviews.

**Example: aversive-habit-devices**

Query: Do self-administered aversive stimuli such as shock wristbands or
snapped rubber bands break habits?

Moves: bind-scope, split-modes, name-mechanisms, route-evidence

Leaves: Separate clinical aversion therapy and its abandonment from consumer
devices; read vendor material as attested about the product and silent on
efficacy; corroborate thin trials before stating plainly; carry the absent
controlled evaluation into Open.

**Example: tests-and-proof**

Query: Can tests and code agree while both violate the intended
specification, and can formal proofs prevent this?

Moves: split-modes, name-mechanisms, bridge-vocabulary, compile-leaves

Leaves: Separate specification choice from implementation conformance;
compare contracts, property testing, refinement and dependent types, theorem
proving, model checking; name each guarantee and trusted base; keep
specification error and common-mode generation failure as boundaries.

**Example: agent-ensemble-benefit**

Query: Do multi-agent ensembles beat one strong model at matched compute?

Moves: audit-premise, bind-scope, pose-rival, route-evidence

Leaves: Bind task family, compute accounting, evaluation; retrieve published
results on both sides; separate framework marketing from measured
matched-compute comparison; expect real survivors from the scan.

**Example: experiment-vocabulary**

Query: Is a three-arm within-subjects study an A/B test, and what makes a
design a bandit instead?

Moves: clarify, bridge-vocabulary, split-modes, route-evidence

Leaves: Retrieve constitutive definitions from method texts and venue
conventions; separate naming convention from statistical design; identify
adaptive allocation as the property that turns arms into a bandit.

**Example: work-visa-routes**

Query: Which visa routes admit a researcher to a US university post, read
both literally and as the underlying goal?

Moves: clarify, bind-scope, split-modes, route-evidence, compile-leaves

Leaves: Branch the stated reading and the likelier goal, then answer both;
give each route one leaf; bind nationality, employer type, cap exemption,
timing; close rules under active litigation as unresolved.

**Example: hardware-search-tree**

Query: How can a splay tree be implemented for modern hardware with low
constant overhead?

Moves: clarify, bind-scope, name-mechanisms, bridge-vocabulary

Leaves: Bind CPU, GPU, FPGA, or ASIC and the operation mix; account for
pointer chasing, branches, rotations, cache locality, write traffic,
concurrency; compare top-down splaying, index-based layouts, batching,
alternative search structures before optimizing splay itself.

**Example: local-model-fit**

Query: Which local language models run usefully in 6 GB of GPU memory, and
does a 24 GB CPU-only server do better?

Moves: bind-scope, name-mechanisms, split-modes, route-evidence

Leaves: Separate quantized weight size from KV-cache growth with context;
name the binding resource per machine, capacity on the GPU and memory
bandwidth on the CPU; retrieve measured throughput per backend; state usable
memory rather than nominal.

**Example: delegated-credentials**

Query: Why are access tokens centrally issued, and could client-signed
requests backed by 7-day certificates and CRLs replace them?

Moves: audit-premise, bind-scope, name-mechanisms, bridge-vocabulary,
compile-leaves

Leaves: Separate centralized token issuance from centralized authorization;
establish the threat model and client key storage; compare bearer tokens,
mutual TLS, proof-of-possession, delegated credentials; analyze 7-day
certificate and CRL freshness, replay, logout, authorization change,
rotation, privacy, operational cost.

**Example: feature-trust-boundary**

Query: What does a remote-control feature do, how is it enabled, and what
trust boundary does it create?

Moves: split-modes, name-mechanisms, route-evidence

Leaves: Retrieve the definition and toggle path from attested documentation;
retrieve the stated permissions and data flow; assign the trust boundary to
the derived chain, since it composes those facts rather than sitting in any
document.

**Example: representation-brokers**

Query: Which agencies represent academics for press and speaking work, and
how does the money differ between them?

Moves: bind-scope, route-evidence, split-modes

Leaves: Retrieve rosters and service descriptions as reported sources;
separate retainer, commission, fee-split structures; hedge each claim to its
source; leave individual staff contacts unresolved, since rosters go stale
and no artifact supports them.

**Example: index-fund-timing**

Query: Is a broad-market equity index fund a good buy during a period of
geopolitical disruption?

Moves: clarify, audit-premise, split-modes, name-mechanisms

Leaves: Resolve what good buy means: horizon, alternative use of the money,
tolerance for drawdown; test the premise that the disruption is not already
priced; retrieve fund composition, fees, measured drawdown-and-recovery
history; keep future return unretrievable and say so.

**Example: multi-party-threads**

Query: How can several people hold one thread with an assistant across the
major vendors, in real time or asynchronously?

Moves: bind-scope, split-modes, route-evidence, compile-leaves

Leaves: Give each vendor independent leaves; separate shared threads from
workspace sharing, link sharing, export; bind plan tier, admin policy,
regional rollout; hedge staged availability.

## Frame checks

Before bundling leaves, verify:

- Every critical ambiguous term resolved or branched.
- Every embedded premise supports `refuted` close while frame stays valid;
  frame names evidence that could refute it.
- Factual, causal, normative, interpretive, feasibility, implementation
  claims use distinct warrants where needed.
- Every leaf names one governing mechanism and one plausible evidence route.
- Leaves independent, jointly cover material question, use mechanism-level
  names.
- Rival premise and answer-flipping boundaries explicit.

## Group and delegate

Delegation starts here, after cycle one; lead retains comprehensive view.
Partition open leaves into disjoint groups by corpus, vocabulary, or
principle; jointly cover open set. Prefer fewer, fuller groups.

Delegate through `/summon divide`, one delegate per group, with brief
`brief` lays out. Summon's mode table decides when group runs inline
instead; ledger state same either way; delegate identity stays outside it.

Delegates read source pages, output closure proposals; they write nothing.
Lead judges each output under summon's `examine`, checks inflated
source-class tags against class table in spine.

## Accept a cycle

1. Deduplicate sources.
2. Judge each close. Use anomalous evidence to test frame. Before
   `retrieved` close, name its falsifier. Close contradicted premises as
   `refuted`; they feed Rival. Close deliberately abandoned leaves as
   `unresolved` with reason `not_pursued` and its explanation.
3. Adapt leaf set: add delegate discoveries as `"origin": "spawned"`; retire
   superseded leaves.
4. Accept spawned leaves, sources, closes, `checkpoints` entry as one
   `record` batch. Checkpoint carries cycle's declared query count (sum of
   delegates' `queries_spent`); same output returns updated yield table. On
   rejection, apply every listed fix, resend once.

## Stop or continue

Falling yield prompts reframe-or-stop decision. Bounds:

- Two unproductive cycles: stop, close remaining open leaves as
  `unresolved`, draft. One authoritative source can complete productive
  cycle.
- Begin saturation judgment one cycle past declared focus.
- Run one to three cycles. Fourth-cycle need triggers reframing and folding.
