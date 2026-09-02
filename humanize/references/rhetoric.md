# Rhetoric patterns (§27-35)

Discourse-level moves: fake depth, self-announcement, staged candor, straw
objections, drafting residue.

### 27. Pretending to reveal a deeper truth

**Watch:** The real question is, at its core, in reality, what really matters, fundamentally, the deeper issue, the heart of the matter
**Problem:** An ordinary point dressed as a hidden truth.
<before>
The real question is whether teams can adapt. At its core, what really matters is organizational readiness.
</before>
<after>
The question is whether teams can adapt. That mostly depends on whether the organization is ready to change its habits.
</after>

The paragraph-scale face: a record of thinking that did not happen, spent to
make an ordinary claim feel earned. Watch: worth sitting with, I keep coming
back to, the question that keeps coming up, here is where I landed, what I
keep running into, the thing that got me, what struck me hardest, I can't
stop thinking about, keep arriving at. Keep the personal detail; drop the
performance of having reflected on it.
<before case="manufactured interiority">
The rest came out over four more messages, which is what two months of turning something over without writing any of it down will do. I keep coming back to that.
</before>
<after>
The rest came out over four more messages. I had been thinking about it since July and had never written any of it down.
</after>

### 28. Announcing the next point

**Watch:** Let's dive in, let's explore, let's break this down, here's what you need to know, now let's look at, without further ado, heads up, quick note, before I forget, there are two things here, three things to know, let me give you four reasons, I'm going to make three points
**Problem:** The next point announced instead of stated, by topic or by count. A casual phrase such as "one thing that bit me" can do the same. Remove the announcement, keeping the content. A count earns its place only when the reader must hold the items open across intervening text.
<before>
Let's dive into how caching works in Next.js. Here's what you need to know.
</before>
<after>
Next.js caches data at multiple layers, including request memoization, the data cache, and the router cache.
</after>
<before case="casual register">
One thing that bit me hard, so pay attention to this part: the webpack dev server doesn't send the CORS header by default.
</before>
<after>
The webpack dev server doesn't send the CORS header by default.
</after>
<before case="announcing the count">
Two things still sit outside the proof. One is the trusted base. The other is the product decision nobody thought hard enough about.
</before>
<after>
The trusted base sits outside the proof: the kernel, the compiler, and the axioms you accept. So does the product decision nobody thought hard enough about.
</after>

### 29. A heading or question repeated in the first sentence

**Problem:** A heading followed by a one-line paragraph that restates it, or an answer that opens by repeating the question it was asked, common in prose that began as a chat reply. Remove the repeated sentence.
<before>
## Performance

Speed matters.

When users hit a slow page, they leave.
</before>
<after>
## Performance

When users hit a slow page, they leave.
</after>
<before case="restated question">
Whether the review burden actually shrinks is a good question. The review burden does shrink, because the reviewed artifact is smaller.
</before>
<after>
The review burden shrinks, because the reviewed artifact is smaller.
</after>

### 30. Writing about the previous version

**Problem:** Documentation and comments should describe current behavior. Mention the previous version only in change logs, release notes, migration guides, and other documents about change.
<before>
This function was added to replace the previous approach of iterating through all items, which caused O(n²) performance.
</before>
<after>
This function uses a hash map for O(1) lookups, avoiding the O(n²) cost of naive iteration.
</after>

### 31. Forced punchlines and dramatic fragments

**Problem:** Every sentence turned into a dramatic closing line. One short sentence can add emphasis; a row of fragments feels forced.
<before>
Then AlphaEvolve arrived. It had no preference for symmetry. No aesthetic prior. No nostalgia for human taste. The old rules were gone.
</before>
<after>
AlphaEvolve changed the search because it did not favor symmetry or human-looking designs. That made some of the older assumptions less useful.
</after>

### 32. Formulaic sayings

**Watch:** X is the Y of Z, X becomes a trap, X is not a tool but a mirror, the language of, the currency of, the architecture of
**Problem:** An ordinary claim turned into a saying that sounds deep but adds no detail. Replace the saying with the specific claim.
<before>
Symmetry is the language of trust. Efficiency becomes a trap when teams forget the human layer.
</before>
<after>
Symmetric layouts often feel more predictable to users. Teams can over-optimize workflows and miss how people actually use them.
</after>

The coined-label face: paradox, trap, creep, divide, vacuum, inversion, tax,
or debt appended to a domain word and presented as established vocabulary,
so an observation reads as a known result. Keep a coinage the writer defines
and then uses, and keep real terms of art (technical debt, scope creep).
<before case="invented compound label">
This is the specification vacuum, and it explains why the rollout stalled.
</before>
<after>
Nobody had written the specification down, which is why the rollout stalled.
</after>

### 33. Fake-candid openings and honesty qualifiers

**Watch:** Honestly?, Look, Here's the thing, The thing is, Let's be honest, Real talk, as standalone hooks or fake-candid pauses before an ordinary point; the honest version, honest caveat, the honest read, the honest limitation, I'll be candid, candidly, anywhere in a sentence
**Problem:** A staged pause or claim of honesty before a routine point. Marking one statement as honest implies the others were not, and the qualifier never survives removal; unlike §24 it hedges the writer's sincerity, not the claim's strength. State the point directly.
<before>
Is it worth the price? Honestly? It depends on how often you'll use it.
</before>
<after>
Whether it's worth the price depends on how often you'll use it.
</after>
<before case="honesty qualifier">
The honest limitation: I cannot say whether either model would pass.
</before>
<after>
I cannot say whether either model would pass.
</after>

### 34. Answering objections no one raised

**Watch:** This isn't (mainly/really) about, I'm not saying/arguing/trying to, To be clear, Don't get me wrong, This is not to say, You could argue/frame this differently but, Some might say... but
**Problem:** An objection answered that appears nowhere in the text. Watch for an unattributed statement about what the writer does not mean, especially when the topic appears nowhere else. A direct claim such as "the API is not thread-safe" is not this pattern.
<before>
This isn't mainly about prompt length, and I'm not arguing that documentation doesn't matter. You could categorize the problem another way, but the issue is whether the agent can use the instruction when it acts.
</before>
<after>
The issue is whether the agent can use the instruction when it acts.
</after>

Remove only the unsupported defense. If it contains a real claim, state that
claim directly. Keep an objection when the text names its source or answers it
in full.

### 35. Rejecting fake alternatives

**Watch:** A tempting option/approach would be, One might be tempted to, An obvious approach would be, You might think... but, It would be easy to just, Some would suggest
**Problem:** An option no reader would consider, introduced only to be rejected in a clause, often residue of an earlier draft. Remove the fake option and state the real constraint directly.
<before>
Session tokens are rotated every 24 hours. A tempting approach would be to rotate them by restarting the auth service on a cron job, but that would drop every active session. Rotation happens in place, and clients refresh transparently.
</before>
<after>
Session tokens are rotated every 24 hours, in place, and clients refresh transparently.
</after>

One rejected option may be valid. Several short, unrelated rejections are a
stronger sign. Ask what new information each sentence adds. If it only records
an earlier edit, rewrite the paragraph around its main point.
