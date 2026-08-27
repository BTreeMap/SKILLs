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
| `compile-leaves` | Scope and mechanisms are stable | Independent, retrievable leaf questions |

A ready frame groups by mechanism, assigns dependent conclusions to the derived
chain, and names evidence that could refute each premise.

## Worked frames

These regression examples preserve retrieval-driving mechanisms, measurements,
and scope while generalizing provenance and wording.

<worked_frames>
	<frame id="comparative-performance">
		<query>How could IEEE 754 non-associativity make a Rust dot product eight times slower than C++?</query>
		<moves>audit-premise, bind-scope, split-modes, name-mechanisms, route-evidence</moves>
		<leaves>Locate and reproduce the eightfold benchmark with source, Rust and C++ versions, compiler flags, and hardware; distinguish IEEE 754 arithmetic from each language's optimization contract; compare vectorization, reduction order, aliasing, and generated assembly; find the fast-math or explicit-SIMD boundary where the result changes.</leaves>
	</frame>

	<frame id="comparative-public-recording">
		<query>Where do major jurisdictions draw the legal boundaries for noncommercial filming in public places?</query>
		<moves>clarify, bind-scope, split-modes, route-evidence, compile-leaves</moves>
		<leaves>Choose representative jurisdictions; separate public property from privately controlled public space; retrieve rules for permits, privacy, personality rights, data protection, recording sound, and later publication; distinguish noncommercial purpose from conduct regulated regardless of profit.</leaves>
	</frame>

	<frame id="distributed-network-failures">
		<query>Beyond incast and microbursts, what degraded network conditions affect modern ML training clusters?</query>
		<moves>bind-scope, name-mechanisms, bridge-vocabulary, route-evidence</moves>
		<leaves>Partition by synchronized traffic, congestion-control response, lossless-fabric feedback, load imbalance, ordering and retransmission, host or NIC stalls, and collective stragglers; retrieve measured signatures and mitigations for each mechanism.</leaves>
	</frame>

	<frame id="moving-reflector">
		<query>Could a curved mirror making small millisecond-scale motions improve wireless signal coverage?</query>
		<moves>clarify</moves>
		<leaves>Clarify whether the mirror rotates, orbits, or oscillates and which radio band it should redirect; then retrieve wavelength-to-curvature limits, actuator response, coherence and fading effects, and reconfigurable-reflector prior art.</leaves>
	</frame>

	<frame id="urban-redevelopment">
		<query>Why might a city fear gentrification despite possible gains in amenities and tax revenue?</query>
		<moves>audit-premise, split-modes, bind-scope, name-mechanisms</moves>
		<leaves>Separate aggregate amenities and revenue from who receives them; test displacement, tenure, tax-base, service, and fiscal-timing mechanisms; distinguish causal evidence from the normative weighting of incumbent residents, newcomers, owners, renters, and city government.</leaves>
	</frame>

	<frame id="modern-adaptation">
		<query>How does a recent film adaptation of an ancient epic reinterpret it for a modern audience?</query>
		<moves>bind-scope, audit-premise, split-modes, route-evidence</moves>
		<leaves>Establish the released version; compare its structure and characters with the source; separate visible choices, attested intent, and critical interpretation; attribute intent through interviews.</leaves>
	</frame>

	<frame id="tests-and-proof">
		<query>Can tests and code agree while both violate the intended specification, and can formal proofs prevent this?</query>
		<moves>split-modes, name-mechanisms, bridge-vocabulary, compile-leaves</moves>
		<leaves>Separate specification choice from implementation conformance; compare contracts, property testing, refinement and dependent types, theorem proving, and model checking; identify each guarantee and trusted base; keep specification error and common-mode generation failure as explicit boundaries.</leaves>
	</frame>

	<frame id="encoded-sum-types">
		<query>How should algebraic data types be represented in C#?</query>
		<moves>clarify, bind-scope, name-mechanisms, route-evidence</moves>
		<leaves>Ask whether the need is modeling, exhaustive matching, runtime representation, serialization, or interop; bind the C# and .NET version; compare records, sealed hierarchies, discriminated encodings, and existing libraries on exhaustiveness, allocation, ergonomics, and boundary decoding.</leaves>
	</frame>

	<frame id="population-geography">
		<query>Why might two-thirds of a country's population live within 100 miles of its border, and what keeps the rest inland?</query>
		<moves>audit-premise, clarify, bind-scope, split-modes, route-evidence</moves>
		<leaves>Verify the estimate, period, geometry, and border definition; map distinct inland populations; test settlement history, climate, transport, labor markets, and amenities; retrieve migration evidence for reasons to stay.</leaves>
	</frame>

	<frame id="hardware-search-tree">
		<query>How can a splay tree be implemented for modern hardware with low constant overhead?</query>
		<moves>clarify, bind-scope, name-mechanisms, bridge-vocabulary</moves>
		<leaves>Bind CPU, GPU, FPGA, or ASIC and the operation mix; account for pointer chasing, branches, rotations, cache locality, write traffic, and concurrency; compare top-down splaying, index-based layouts, batching, and alternative search structures before optimizing splay itself.</leaves>
	</frame>

	<frame id="delegated-credentials">
		<query>Why are access tokens centrally issued, and could client-signed requests backed by 7-day certificates and CRLs replace them?</query>
		<moves>audit-premise, bind-scope, name-mechanisms, bridge-vocabulary, compile-leaves</moves>
		<leaves>Define centralized token issuance separately from centralized authorization; establish the threat model and client key storage; compare bearer tokens, mutual TLS, proof-of-possession, and delegated credentials; analyze 7-day certificate and CRL freshness, replay, logout, authorization change, rotation, privacy, and operational cost.</leaves>
	</frame>

	<frame id="https-filter">
		<query>Does an Android ad blocker that filters HTTPS transparently pass through a browser's TLS connection, or terminate and re-establish it?</query>
		<moves>bind-scope, split-modes, name-mechanisms, route-evidence</moves>
		<leaves>Bind the blocker, Android version, browser, and filtering mode; distinguish a local VPN tunnel from HTTPS interception; trace certificate installation, browser trust, downstream termination, upstream TLS negotiation, and certificate-pinning exceptions through documentation, source where available, and packet or certificate observations.</leaves>
	</frame>
</worked_frames>

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
