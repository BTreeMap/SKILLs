# Framing: from question to leaves

Use this scaffold whenever the probe stays open. Compose its moves into a frame
around governing mechanisms; most queries mix several modes.

## Ready frame

Build every field before registering leaves:

- scope: time, place, jurisdiction, version, population, workload, platform,
  and stakeholder boundaries that can change the answer;
- premises: every embedded factual or causal claim marked for confirmation or
  refutation;
- modes: factual, causal, normative, interpretive, feasibility, or
  implementation claims separated where their evidence and warrants differ;
- mechanisms: the laws, incentives, protocols, physical processes, or cost
  drivers that decide the question;
- evidence routes: the expected artifact and source class, using the class
  definitions in the spine, for each retrievable claim;
- rival: the strongest plausible premise or account that could reverse the
  emerging answer;
- leaves: 3-10 independent questions, each settled by one retrieval act.

For critical ambiguity, ask one focused question. If clarification is
unavailable, branch each plausible reading and use the branch point as Boundary
material. Put dependent sub-questions in the derived chain.

## Framing moves

Apply each contributing move in order. Re-run `clarify` when evidence exposes a
new interpretation.

| Move | Trigger | Product |
| --- | --- | --- |
| `clarify` | Two readings invoke different mechanisms or evidence | One user question, or explicit branches |
| `bind-scope` | The answer changes across context | Named dimensions and boundaries |
| `audit-premise` | The query embeds a statistic, history, comparison, or causal claim | A premise leaf that may close `refuted` |
| `split-modes` | Facts, causes, values, interpretations, feasibility, or implementation are mixed | Separate claims with separate warrants |
| `name-mechanisms` | Topic nouns conceal what determines the answer | Governing principles and cost drivers |
| `bridge-vocabulary` | The idea may exist under specialist terminology | Search terms and prior-art families |
| `route-evidence` | A claim lacks a natural retrieval target | Expected artifact and source class |
| `pose-rival` | The strongest contrary account lives outside the query's own premises | The rival field, with a leaf that may close `refuted` |
| `compile-leaves` | Scope and mechanisms are stable | Independent, retrievable leaf questions |

A ready frame groups by mechanism, assigns dependent conclusions to the derived
chain, and names evidence that could refute each premise.

## Worked frames

<examples for="framing">

<example id="comparative-performance">
<query>How could IEEE 754 non-associativity make a Rust dot product eight times slower than C++?</query>
<moves>audit-premise, bind-scope, split-modes, name-mechanisms, route-evidence</moves>
<leaves>Reproduce the eightfold benchmark with source, Rust and C++ versions, compiler flags, hardware; separate IEEE 754 arithmetic from each language's optimization contract; compare vectorization, reduction order, aliasing, generated assembly; locate the fast-math or explicit-SIMD boundary where the result changes.</leaves>
</example>

<example id="shared-credential-writes">
<query>Would a broker process serializing access fix a shared credentials file that concurrent sessions keep corrupting?</query>
<moves>audit-premise, pose-rival, name-mechanisms, split-modes, route-evidence</moves>
<leaves>Test the premise that interleaved writes cause the corruption; retrieve the rival account where single-use refresh-token rotation invalidates a stored grant; compare file locking, atomic replace, and broker serialization against the interval that needs exclusion; locate the platform's documented credential-helper seam.</leaves>
</example>

<example id="comparative-public-recording">
<query>Where do major jurisdictions draw the legal boundaries for noncommercial filming in public places?</query>
<moves>clarify, bind-scope, split-modes, route-evidence, compile-leaves</moves>
<leaves>Choose representative jurisdictions; separate public property from privately controlled public space; retrieve rules on permits, privacy, personality rights, data protection, sound recording, later publication; distinguish noncommercial purpose from conduct regulated regardless of profit.</leaves>
</example>

<example id="control-plane-placement">
<query>Which of six spread regions should host a centralized control plane once latency to all of them counts?</query>
<moves>bind-scope, split-modes, name-mechanisms, route-evidence</moves>
<leaves>Separate worst-case latency from mean and from the tail the control protocol feels; retrieve measured inter-region round trips; weigh failure domains, data residency, egress cost; name the traffic pattern that decides between one central plane and regional planes.</leaves>
</example>

<example id="petition-timing">
<query>Is a ten-business-day filing delay on a work petition worth trading for a conference trip before a fixed start date?</query>
<moves>audit-premise, split-modes, bind-scope, name-mechanisms</moves>
<leaves>Confirm the premium adjudication clock, what pauses it, and what the receipt date sets; surface the buried variable, since travel while a change-of-status petition is pending reads as abandonment; bind filing type, current status, consular versus in-country processing; name where licensed judgment is required without letting that replace retrieval.</leaves>
</example>

<example id="distributed-network-failures">
<query>Beyond incast and microbursts, what degraded network conditions affect modern ML training clusters?</query>
<moves>bind-scope, name-mechanisms, bridge-vocabulary, route-evidence</moves>
<leaves>Partition by synchronized traffic, congestion-control response, lossless-fabric feedback, load imbalance, ordering and retransmission, host or NIC stalls, collective stragglers; retrieve measured signatures and mitigations per mechanism.</leaves>
</example>

<example id="research-crowdfunding">
<query>Can crowdfunding fund a research lab, what predicts campaign success, and where does the money legally land?</query>
<moves>split-modes, name-mechanisms, route-evidence, compile-leaves</moves>
<leaves>Retrieve measured campaign samples for predictors, holding existing audience apart from platform choice; route the destination and tax-receipt question to constitutive platform and university policy; close donation framing unresolved where the literature is silent instead of borrowing an adjacent nonprofit result.</leaves>
</example>

<example id="tunneled-path-latency">
<query>How much latency does tunneling a service through a third region add over a direct path, and what decides the increase?</query>
<moves>bind-scope, name-mechanisms, route-evidence, split-modes</moves>
<leaves>Bind endpoints, tunnel type, provider; decompose the increase into physical path length, peering and transit choice, encapsulation and encryption cost, queueing under load; retrieve looking-glass and probe measurements; report a range rather than one figure.</leaves>
</example>

<example id="moving-reflector">
<query>Could a curved mirror making small millisecond-scale motions improve wireless signal coverage?</query>
<moves>clarify, name-mechanisms, bridge-vocabulary</moves>
<leaves>Clarify whether the mirror rotates, orbits, or oscillates, and which radio band it redirects; retrieve wavelength-to-curvature limits, actuator response, coherence and fading effects, reconfigurable-reflector prior art.</leaves>
</example>

<example id="downtown-parking">
<query>Which garage near a downtown restaurant is the best value for an evening?</query>
<moves>bind-scope, route-evidence, audit-premise, split-modes</moves>
<leaves>Take operator rate pages as constitutive on price; treat review aggregators as reported on access and safety; bind evening hours, event surcharges, walking distance; reconcile published capacity against the operator's own notice of reduced spaces.</leaves>
</example>

<example id="urban-redevelopment">
<query>Why might a city fear gentrification despite possible gains in amenities and tax revenue?</query>
<moves>audit-premise, split-modes, bind-scope, name-mechanisms</moves>
<leaves>Separate aggregate amenities and revenue from who receives them; test displacement, tenure, tax-base, service, fiscal-timing mechanisms; separate causal evidence from the normative weighting across incumbent residents, newcomers, owners, renters, city government.</leaves>
</example>

<example id="durable-scheduled-state">
<query>Why do scheduled reminders vanish when a process restarts, and does a persisted outbox beat periodic polling for timezone-aware delivery?</query>
<moves>audit-premise, name-mechanisms, split-modes, compile-leaves</moves>
<leaves>Locate the state living only in process memory; separate durability from scheduling policy; compare a persisted outbox of due events against a periodic sweep on write amplification, clock skew, DST transitions, retries, duplicate delivery; retrieve documented scheduler and timezone-database behavior.</leaves>
</example>

<example id="modern-adaptation">
<query>How does a recent film adaptation of an ancient epic reinterpret it for a modern audience?</query>
<moves>bind-scope, audit-premise, split-modes, route-evidence</moves>
<leaves>Establish the released version; compare structure and characters against the source; separate visible choices, attested intent, critical interpretation; attribute intent through interviews.</leaves>
</example>

<example id="aversive-habit-devices">
<query>Do self-administered aversive stimuli such as shock wristbands or snapped rubber bands break habits?</query>
<moves>bind-scope, split-modes, name-mechanisms, route-evidence</moves>
<leaves>Separate clinical aversion therapy and its abandonment from consumer devices; read vendor material as attested about the product and silent on efficacy; corroborate thin trials before stating plainly; carry the absent controlled evaluation into Open.</leaves>
</example>

<example id="tests-and-proof">
<query>Can tests and code agree while both violate the intended specification, and can formal proofs prevent this?</query>
<moves>split-modes, name-mechanisms, bridge-vocabulary, compile-leaves</moves>
<leaves>Separate specification choice from implementation conformance; compare contracts, property testing, refinement and dependent types, theorem proving, model checking; name each guarantee and trusted base; keep specification error and common-mode generation failure as boundaries.</leaves>
</example>

<example id="agent-ensemble-benefit">
<query>Do multi-agent ensembles beat one strong model at matched compute?</query>
<moves>audit-premise, bind-scope, pose-rival, route-evidence</moves>
<leaves>Bind task family, compute accounting, evaluation; retrieve published results on both sides; separate framework marketing from measured matched-compute comparison; expect real survivors from the sweep.</leaves>
</example>

<example id="encoded-sum-types">
<query>How should algebraic data types be represented in C#?</query>
<moves>clarify, bind-scope, name-mechanisms, route-evidence</moves>
<leaves>Ask whether the need is modeling, exhaustive matching, runtime representation, serialization, or interop; bind the C# and .NET version; compare records, sealed hierarchies, discriminated encodings, existing libraries on exhaustiveness, allocation, ergonomics, boundary decoding.</leaves>
</example>

<example id="experiment-vocabulary">
<query>Is a three-arm within-subjects study an A/B test, and what makes a design a bandit instead?</query>
<moves>clarify, bridge-vocabulary, split-modes, route-evidence</moves>
<leaves>Retrieve constitutive definitions from method texts and venue conventions; separate naming convention from statistical design; identify adaptive allocation as the property that turns arms into a bandit.</leaves>
</example>

<example id="population-geography">
<query>Why might two-thirds of a country's population live within 100 miles of its border, and what keeps the rest inland?</query>
<moves>audit-premise, clarify, bind-scope, split-modes, route-evidence</moves>
<leaves>Verify the estimate, period, geometry, border definition; map distinct inland populations; test settlement history, climate, transport, labor markets, amenities; retrieve migration evidence for reasons to stay.</leaves>
</example>

<example id="work-visa-routes">
<query>Which visa routes admit a researcher to a US university post, read both literally and as the underlying goal?</query>
<moves>clarify, bind-scope, split-modes, route-evidence, compile-leaves</moves>
<leaves>Branch the stated reading and the likelier goal, then answer both; give each route one leaf; bind nationality, employer type, cap exemption, timing; close rules under active litigation as unresolved.</leaves>
</example>

<example id="hardware-search-tree">
<query>How can a splay tree be implemented for modern hardware with low constant overhead?</query>
<moves>clarify, bind-scope, name-mechanisms, bridge-vocabulary</moves>
<leaves>Bind CPU, GPU, FPGA, or ASIC and the operation mix; account for pointer chasing, branches, rotations, cache locality, write traffic, concurrency; compare top-down splaying, index-based layouts, batching, alternative search structures before optimizing splay itself.</leaves>
</example>

<example id="local-model-fit">
<query>Which local language models run usefully in 6 GB of GPU memory, and does a 24 GB CPU-only server do better?</query>
<moves>bind-scope, name-mechanisms, split-modes, route-evidence</moves>
<leaves>Separate quantized weight size from KV-cache growth with context; name the binding resource per machine, capacity on the GPU and memory bandwidth on the CPU; retrieve measured throughput per backend; state usable memory rather than nominal.</leaves>
</example>

<example id="delegated-credentials">
<query>Why are access tokens centrally issued, and could client-signed requests backed by 7-day certificates and CRLs replace them?</query>
<moves>audit-premise, bind-scope, name-mechanisms, bridge-vocabulary, compile-leaves</moves>
<leaves>Separate centralized token issuance from centralized authorization; establish the threat model and client key storage; compare bearer tokens, mutual TLS, proof-of-possession, delegated credentials; analyze 7-day certificate and CRL freshness, replay, logout, authorization change, rotation, privacy, operational cost.</leaves>
</example>

<example id="feature-trust-boundary">
<query>What does a remote-control feature do, how is it enabled, and what trust boundary does it create?</query>
<moves>split-modes, name-mechanisms, route-evidence</moves>
<leaves>Retrieve the definition and toggle path from attested documentation; retrieve the stated permissions and data flow; assign the trust boundary to the derived chain, since it composes those facts rather than sitting in any document.</leaves>
</example>

<example id="https-filter">
<query>Does an Android ad blocker that filters HTTPS transparently pass through a browser's TLS connection, or terminate and re-establish it?</query>
<moves>bind-scope, split-modes, name-mechanisms, route-evidence</moves>
<leaves>Bind the blocker, Android version, browser, filtering mode; separate a local VPN tunnel from HTTPS interception; trace certificate installation, browser trust, downstream termination, upstream TLS negotiation, certificate-pinning exceptions through documentation, source where available, packet or certificate observations.</leaves>
</example>

<example id="representation-brokers">
<query>Which agencies represent academics for press and speaking work, and how does the money differ between them?</query>
<moves>bind-scope, route-evidence, split-modes</moves>
<leaves>Retrieve rosters and service descriptions as reported sources; separate retainer, commission, fee-split structures; hedge each claim to its source; leave individual staff contacts unresolved, since rosters go stale and no artifact supports them.</leaves>
</example>

<example id="index-fund-timing">
<query>Is a broad-market equity index fund a good buy during a period of geopolitical disruption?</query>
<moves>clarify, audit-premise, split-modes, name-mechanisms</moves>
<leaves>Resolve what good buy means: horizon, alternative use of the money, tolerance for drawdown; test the premise that the disruption is not already priced; retrieve fund composition, fees, measured drawdown-and-recovery history; keep future return unretrievable and say so.</leaves>
</example>

<example id="fund-price-mechanism">
<query>How does an exchange-traded fund's net asset value relate to its traded price during volatility?</query>
<moves>name-mechanisms, bridge-vocabulary, route-evidence</moves>
<leaves>Retrieve creation and redemption from constitutive issuer and exchange documentation; name authorized-participant arbitrage as the coupling; separate intraday indicative value from end-of-day NAV; retrieve measured premium and discount data from stressed periods.</leaves>
</example>

<example id="multi-party-threads">
<query>How can several people hold one thread with an assistant across the major vendors, in real time or asynchronously?</query>
<moves>bind-scope, split-modes, route-evidence, compile-leaves</moves>
<leaves>Give each vendor independent leaves; separate shared threads from workspace sharing, link sharing, export; bind plan tier, admin policy, regional rollout; hedge staged availability.</leaves>
</example>
</examples>

## Completion checks

Before handing the frame back to `explore`, verify:

- every critical ambiguous term is resolved or branched;
- every embedded premise supports a `refuted` close while the frame remains valid;
- factual, causal, normative, interpretive, feasibility, and implementation
  claims use distinct warrants where needed;
- every leaf names one governing mechanism and one plausible evidence route;
- leaves are independent, jointly cover the material question, and use
  mechanism-level names;
- the rival premise and answer-flipping boundaries are explicit.
