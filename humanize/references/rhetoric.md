# Rhetoric patterns (§27-35)

Discourse-level moves: fake depth, self-announcement, staged candor, straw
objections, drafting residue. Routing cues live in the detection index; this
file owns the watch-lists, problems, and examples.

### 27. Pretending to reveal a deeper truth

**Watch:** The real question is, at its core, in reality, what really matters, fundamentally, the deeper issue, the heart of the matter
**Problem:** An ordinary point dressed as a hidden truth.
<before>
The real question is whether teams can adapt. At its core, what really matters is organizational readiness.
</before>
<after>
The question is whether teams can adapt. That mostly depends on whether the organization is ready to change its habits.
</after>

### 28. Announcing the next point

**Watch:** Let's dive in, let's explore, let's break this down, here's what you need to know, now let's look at, without further ado, heads up, quick note, before I forget
**Problem:** The next point announced instead of stated. A casual phrase such as "one thing that bit me" can do the same. Remove the announcement, not just its formal tone.
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

### 29. A heading repeated in the first sentence

**Problem:** A heading followed by a one-line paragraph that restates the heading before the real content begins. Remove the repeated sentence.
<before>
## Performance

Speed matters.

When users hit a slow page, they leave.
</before>
<after>
## Performance

When users hit a slow page, they leave.
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

### 33. Fake-candid openings

**Watch:** Honestly?, Look, Here's the thing, The thing is, Let's be honest, Real talk, as standalone hooks or fake-candid pauses before an ordinary point
**Problem:** A staged pause or claim of honesty before a routine point. State the point directly.
<before>
Is it worth the price? Honestly? It depends on how often you'll use it.
</before>
<after>
Whether it's worth the price depends on how often you'll use it.
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
