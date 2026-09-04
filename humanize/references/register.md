# Register patterns (§36-40)

What survives a vocabulary scrub: flat rhythm, metaphor density, manufactured
salience, compressed jargon, leaked reasoning. §36 and §39 are structural,
§38 and §40 rhetorical, §37 lexical: there density is the tell and one
instance is English.

### 36. Uniform sentence rhythm

**Measure:** the coefficient of variation of sentence length, standard
deviation over mean, in words, per block of about 40 sentences. Human prose
runs 0.55 to 0.75 with a block floor near 0.4; unedited model output sits
near 0.2 to 0.3. Flag a block under 0.45, then read it aloud: the number is
a prompt, and the writer's own baseline replaces it when a sample exists.
**Problem:** Every sentence lands at the same middle length. The ear hears a
metronome even after every flagged phrase is gone.
**Fix:** Merge two adjacent sentences that share a subject; split one
sentence carrying two independent claims. Adding a short sentence for effect
produces §31.

<before>
The validator runs before the request reaches the handler. It checks each field against the schema. It reports every invalid field to the caller. The caller decides whether to retry the request.
</before>

<after>
The validator checks every field against the schema before the request reaches the handler, then reports the invalid ones. The caller decides whether to retry.
</after>

<commands for="measure">
python3 -c "import re,sys,statistics as s;t=re.sub(r'\s+',' ',open(sys.argv[1]).read());n=[len(x.split()) for x in re.split(r'(?<=[.!?])\s+(?=[A-Z\"(])',t) if 3<=len(x.split())<=120];print([round(s.pstdev(b)/s.mean(b),2) for b in (n[i:i+40] for i in range(0,len(n)-39,40))])" <file>
</commands>

### 37. Placement and weight verbs

**Watch:** lives (in), sits (in, with, at), holds, carries, rides along,
hands you, surfaces (verb), reaches for, does the work, load-bearing, the
engine of, the seam
**Problem:** Abstract nouns given a place, a weight, or hands, in volume.
Human prose uses these verbs literally and rarely; model prose uses them
figuratively at twenty times the rate. Flag figurative instances above two
per thousand words, or three in one paragraph. Below that, leave them: one
placement verb is often the best sentence on the page.

<before>
The risk lives in the handoff. The retry policy carries most of the weight, and the timeout is the load-bearing setting, so the config file is where the argument sits.
</before>

<after>
The handoff is where failures happen. The retry policy matters most, the timeout is the setting that decides it, and both are in the config file.
</after>

### 38. Manufactured salience

**Watch:** the one thing, the single most, the one that surprised me most,
if I had to pick one, the most interesting part, where this matters most,
the best one is, precisely the X you
**Problem:** A ranking the writer never made, used to steer attention the
content should steer by itself. A superlative the text earns stays: after
four numbers, "the largest" is a fact.

<before>
The one thing to understand is the oracle split. The most interesting part is that the agent defines the scored function as a copy of the specification's own witness.
</before>

<after>
The oracle split is sharper than the others: the agent defines the scored function as a copy of the specification's own witness.
</after>

### 39. Compressed jargon

**Problem:** Nouns stacked as modifiers, coined hyphen compounds, and
half-sentences with no connective tissue: the register a coding agent drifts
into over a long session, precise for the engineer already in context and
opaque to everyone else. Heuristic: three or more nouns in a row with no
determiner or preposition between them, or two invented hyphen compounds in
one sentence. Expand each stack into the sentence it abbreviates.

<before>
Cap the study-lifecycle handlers so a hung study can't wedge the deep-link path; this is the co-located-demo case, and it needs a review surface for the human.
</before>

<after>
Limit how long a study's handlers may run, so one hung study cannot block deep links. The failure shows up when a demo runs on the same machine, and a person needs somewhere to read the result.
</after>

### 40. Reasoning residue

**Watch:** the single most important correction, the corrections matter
because, does not survive contact with, the prior runs the other way, what
holds up / what was wrong, here is the smoking gun, that is precisely the X
**Problem:** Prose written as an audit of an earlier draft the reader never
saw. The model's checking voice spilled into the answer: verdicts on
corrections, refutations of claims nobody made, a case argued to itself.
Near §30 and §35 (drafting residue) and §34 (unraised objections). State the
finding; delete the trial.

<before>
The single most important correction: the cache is per-process. That does not survive contact with the deployment diagram, where the prior runs the other way. What holds up: the eviction policy.
</before>

<after>
The cache is per-process, which the deployment diagram contradicts. The eviction policy is correct as described.
</after>
