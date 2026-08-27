# Framing: from question to leaves

Use this teaching scaffold whenever the probe stays open. It supplies the
high-level framing moves a lead model may not infer unaided. Compose moves;
never classify a query as one question type. A real query often mixes several
modes, and its useful frame follows the governing mechanisms rather than its
surface nouns.

## Ready frame

Construct a frame with all of these products before registering leaves:

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

A critical ambiguity produces one focused clarification question instead of a
frame. If clarification is unavailable, preserve each plausible reading as an
explicit branch and make the branch point Boundary material. A sub-question
that depends on another leaf's result is a derived link, never another leaf.

## Framing moves

Apply these moves in order, skipping only moves that add nothing. Re-run
`clarify` when evidence exposes a new interpretation.

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

Reject a topic outline such as components named after the query's nouns. Reject
a leaf that asks for a conclusion requiring another leaf first. Reject a frame
that can confirm its premise but names no evidence that could refute it.

## Worked frames

Treat these as regression examples for the moves, not partitions of the query
space.

<worked_frames>
	<frame id="comparative-performance">
		<query>Why is one numerical reduction reportedly much slower than another under strict floating-point semantics?</query>
		<moves>audit-premise, bind-scope, split-modes, name-mechanisms, route-evidence</moves>
		<leaves>Locate and reproduce the reported benchmark with source, versions, flags, and hardware; distinguish standard arithmetic from each implementation's optimization contract; compare vectorization, reduction order, aliasing, and generated instructions; find the optimization boundary where the result changes.</leaves>
	</frame>

	<frame id="comparative-public-recording">
		<query>How do jurisdictions regulate noncommercial recording in public places?</query>
		<moves>clarify, bind-scope, split-modes, route-evidence, compile-leaves</moves>
		<leaves>Choose representative jurisdictions; separate public property from privately controlled public space; retrieve rules for permits, privacy, personality rights, data protection, recording sound, and later publication; distinguish noncommercial purpose from conduct regulated regardless of profit.</leaves>
	</frame>

	<frame id="distributed-network-failures">
		<query>What transient network failures can degrade distributed training workloads?</query>
		<moves>bind-scope, name-mechanisms, bridge-vocabulary, route-evidence</moves>
		<leaves>Partition by synchronized traffic, congestion-control response, lossless-fabric feedback, load imbalance, ordering and retransmission, host or NIC stalls, and collective stragglers; retrieve measured signatures and mitigations for each mechanism instead of collecting symptom names.</leaves>
	</frame>

	<frame id="moving-reflector">
		<query>What could a curved reflector moving at short intervals do?</query>
		<moves>clarify</moves>
		<leaves>Do not search yet: rotating, orbiting, oscillating, and beam-steering interpretations invoke different mechanics and optics. Ask what the reflector should accomplish, its motion, scale, and operating wavelength.</leaves>
	</frame>

	<frame id="urban-redevelopment">
		<query>Why might a city oppose redevelopment that could raise amenities and tax revenue?</query>
		<moves>audit-premise, split-modes, bind-scope, name-mechanisms</moves>
		<leaves>Separate aggregate amenities and revenue from who receives them; test displacement, tenure, tax-base, service, and fiscal-timing mechanisms; distinguish causal evidence from the normative weighting of incumbent residents, newcomers, owners, renters, and city government.</leaves>
	</frame>

	<frame id="modern-adaptation">
		<query>How might a recent adaptation reinterpret a classic story for a modern audience?</query>
		<moves>bind-scope, audit-premise, split-modes, route-evidence</moves>
		<leaves>Establish which released version is in scope; compare its structure and character choices with the source work; separate choices visible in the adaptation, intent attested in interviews, and interpretations argued by critics; never attribute an inference to the creator as stated intent.</leaves>
	</frame>

	<frame id="tests-and-proof">
		<query>Can tests and code agree while both violate the intended specification, and can formal proofs prevent this?</query>
		<moves>split-modes, name-mechanisms, bridge-vocabulary, compile-leaves</moves>
		<leaves>Separate the specification-oracle problem from implementation conformance; compare contracts, property testing, refinement and dependent types, theorem proving, and model checking; identify what each proves and its trusted base; preserve specification error and agent-generated common-mode failure as boundaries no proof technique erases by itself.</leaves>
	</frame>

	<frame id="encoded-sum-types">
		<query>How should a language without native algebraic data types represent them?</query>
		<moves>clarify, bind-scope, name-mechanisms, route-evidence</moves>
		<leaves>Ask whether the need is modeling, exhaustive matching, runtime representation, serialization, or interop; bind the language and runtime version; compare native closed-hierarchy encodings with existing project libraries on exhaustiveness, allocation, ergonomics, and boundary decoding.</leaves>
	</frame>

	<frame id="population-geography">
		<query>Why might most of a country's population cluster near its boundary, and what keeps the rest farther inland?</query>
		<moves>audit-premise, clarify, bind-scope, split-modes, route-evidence</moves>
		<leaves>Verify the fraction, period, geometry, and what counts as a boundary; map the remaining population without treating it as one lifestyle; test settlement history, climate, transport, labor-market, and amenity mechanisms; use migration evidence rather than assuming everyone shares one reason to stay.</leaves>
	</frame>

	<frame id="hardware-search-tree">
		<query>How can a self-adjusting search tree be made hardware-friendly with low constant overhead?</query>
		<moves>clarify, bind-scope, name-mechanisms, bridge-vocabulary</moves>
		<leaves>Bind the hardware target and operation mix; account for pointer chasing, branches, rotations, cache locality, write traffic, and concurrency; compare restructuring strategies, index-based layouts, batching, and alternative search structures before optimizing the named structure.</leaves>
	</frame>

	<frame id="delegated-credentials">
		<query>Why are credentials centrally issued, and could short-lived client certificates replace them?</query>
		<moves>audit-premise, bind-scope, name-mechanisms, bridge-vocabulary, compile-leaves</moves>
		<leaves>Define centralized issuance separately from centralized authorization; establish the threat model and client key storage; compare bearer credentials, client certificates, proof-of-possession, and delegated credentials; analyze revocation freshness, replay, authorization change, rotation, privacy, and operational cost.</leaves>
	</frame>

	<frame id="https-filter">
		<query>Does a local HTTPS filter terminate and re-establish a browser's TLS connections?</query>
		<moves>bind-scope, split-modes, name-mechanisms, route-evidence</moves>
		<leaves>Bind the implementation, version, platform, browser, and filtering mode; distinguish local tunneling or routing from HTTPS filtering; trace certificate installation, trust decisions, connection termination, upstream TLS, and pinned-certificate exceptions through documentation, source where available, and packet or certificate observations.</leaves>
	</frame>
</worked_frames>

## Completion checks

Before handing the frame back to `explore`, verify:

- every critical ambiguous term is resolved or branched;
- every embedded premise can close `refuted` without breaking the frame;
- factual, causal, normative, interpretive, feasibility, and implementation
	claims use distinct warrants where needed;
- every leaf names one governing mechanism and one plausible evidence route;
- leaves are independent, jointly cover the material question, and contain no
	surface-topic placeholders;
- the rival premise and answer-flipping boundaries are explicit.
