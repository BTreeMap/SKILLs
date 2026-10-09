# Rhetoric patterns (§27-35)

### 27. Pretending to reveal a deeper truth

**Watch:** The real question is, at its core, in reality, what really
matters, fundamentally, the deeper issue, the heart of the matter.
Manufactured interiority: worth sitting with, I keep coming back to, the
question that keeps coming up, here is where I landed, what I keep running
into, the thing that got me, what struck me hardest, I can't stop thinking
about, keep arriving at.

**Problem:** Ordinary point dressed as hidden truth. At paragraph scale,
record of thinking that did not happen, spent to make ordinary claim feel
earned: keep personal detail; drop performance of having reflected on it.

**Example**

Before: The real question is whether teams can adapt. At its core, what
really matters is organizational readiness.

After: The question is whether teams can adapt. That mostly depends on
whether the organization is ready to change its habits.

**Example: manufactured interiority**

Before: The rest came out over four more messages, which is what two months
of turning something over without writing any of it down will do. I keep
coming back to that.

After: The rest came out over four more messages. I had been thinking about
it since July and had never written any of it down.

### 28. Announcing the next point

**Watch:** Let's dive in, let's explore, let's break this down, here's what
you need to know, now let's look at, without further ado, heads up, quick
note, before I forget, there are two things here, three things to know, let
me give you four reasons, I'm going to make three points

**Problem:** Next point announced instead of stated, by topic or by count.
Casual phrase such as "one thing that bit me" can do same. Remove
announcement, keep content.

**Exceptions:** Count reader must hold. Count case targets decoration; count
helping reader track items across intervening text is navigation.

**Example**

Before: Let's dive into how caching works in Next.js. Here's what you need
to know.

After: Next.js caches data at multiple layers, including request
memoization, the data cache, and the router cache.

**Example: casual register**

Before: One thing that bit me hard, so pay attention to this part: the
webpack dev server doesn't send the CORS header by default.

After: The webpack dev server doesn't send the CORS header by default.

**Example: announcing the count**

Before: Two things still sit outside the proof. One is the trusted base. The
other is the product decision nobody thought hard enough about.

After: The trusted base sits outside the proof: the kernel, the compiler,
and the axioms you accept. So does the product decision nobody thought hard
enough about.

### 29. A heading or question repeated in the first sentence

**Problem:** Heading followed by one-line paragraph restating it, or answer
opening by repeating question it was asked, common in prose that began as
chat reply. Remove repeated sentence.

**Example**

Before:

```markdown
## Performance

Speed matters.

When users hit a slow page, they leave.
```

After:

```markdown
## Performance

When users hit a slow page, they leave.
```

**Example: restated question**

Before: Whether the review burden actually shrinks is a good question. The
review burden does shrink, because the reviewed artifact is smaller.

After: The review burden shrinks, because the reviewed artifact is smaller.

### 30. Writing about the previous version

**Problem:** Documentation and comments should describe current behavior.
Mention previous version only in change logs, release notes, migration
guides, other documents about change.

**Example**

Before: This function was added to replace the previous approach of
iterating through all items, which caused O(n²) performance.

After: This function uses a hash map for O(1) lookups, avoiding the O(n²)
cost of naive iteration.

### 31. Forced punchlines and dramatic fragments

**Problem:** Every sentence turned into dramatic closing line.

**Exceptions:** One short sentence for emphasis. Flag dramatic fragments
only when several appear in a row.

**Example**

Before: Then AlphaEvolve arrived. It had no preference for symmetry. No
aesthetic prior. No nostalgia for human taste. The old rules were gone.

After: AlphaEvolve changed the search because it did not favor symmetry or
human-looking designs. That made some of the older assumptions less useful.

### 32. Formulaic sayings

**Watch:** X is the Y of Z, X becomes a trap, X is not a tool but a mirror,
the language of, the currency of, the architecture of. Coined labels:
paradox, trap, creep, divide, vacuum, inversion, tax, or debt appended to a
domain word.

**Problem:** Ordinary claim turned into saying that sounds deep but adds no
detail. Replace saying with specific claim. Coined label presented as
established vocabulary makes observation read as known result.

**Exceptions:** Real terms of art and defined coinages. Technical debt,
scope creep, label writer defines and then uses are vocabulary; coined-label
case targets undefined label posing as one. Suffix match alone is weak: tax,
debt, trap are ordinary literal words.

**Example**

Before: Symmetry is the language of trust. Efficiency becomes a trap when
teams forget the human layer.

After: Symmetric layouts often feel more predictable to users. Teams can
over-optimize workflows and miss how people actually use them.

**Example: invented compound label**

Before: This is the specification vacuum, and it explains why the rollout
stalled.

After: Nobody had written the specification down, which is why the rollout
stalled.

### 33. Fake-candid openings and honesty qualifiers

**Watch:** Honestly?, Look, Here's the thing, The thing is, Let's be honest,
Real talk, as standalone hooks or fake-candid pauses before an ordinary
point; the honest version, honest caveat, the honest read, the honest
limitation, I'll be candid, candidly, anywhere in a sentence

**Problem:** Staged pause or claim of honesty before routine point. Marking
one statement honest implies others were not; qualifier never survives
removal; unlike §24 it hedges writer's sincerity, not claim's strength.
State point directly.

**Exceptions:** "Honestly" or "look" mid-sentence in casual writing, and
quoted speech, stay. Sign is standalone theatrical opener, or writer marking
own claim as the honest one.

**Example**

Before: Is it worth the price? Honestly? It depends on how often you'll use
it.

After: Whether it's worth the price depends on how often you'll use it.

**Example: honesty qualifier**

Before: The honest limitation: I cannot say whether either model would pass.

After: I cannot say whether either model would pass.

### 34. Answering objections no one raised

**Watch:** This isn't (mainly/really) about, I'm not saying/arguing/trying
to, To be clear, Don't get me wrong, This is not to say, You could
argue/frame this differently but, Some might say... but

**Problem:** Objection answered that appears nowhere in text. Watch for
unattributed statement about what writer does not mean, especially when
topic appears nowhere else. Remove only unsupported defense. Contains real
claim: state that claim directly.

**Exceptions:** Keep objection when text names its source or answers it in
full. Direct claim such as "the API is not thread-safe" is not this pattern.

**Example**

Before: This isn't mainly about prompt length, and I'm not arguing that
documentation doesn't matter. You could categorize the problem another way,
but the issue is whether the agent can use the instruction when it acts.

After: The issue is whether the agent can use the instruction when it acts.

### 35. Rejecting fake alternatives

**Watch:** A tempting option/approach would be, One might be tempted to, An
obvious approach would be, You might think... but, It would be easy to just,
Some would suggest

**Problem:** Option no reader would consider, introduced only to be rejected
in a clause, often residue of earlier draft. Remove fake option, state real
constraint directly. Ask what new information each sentence adds; only
records earlier edit: rewrite paragraph around its main point.

**Exceptions:** Real alternatives. Keep options reader may consider in
design document, tutorial, or argument; remove only unlikely option text
dismisses and never uses again. One rejected option may be valid; several
short, unrelated rejections are stronger sign.

**Example**

Before: Session tokens are rotated every 24 hours. A tempting approach would
be to rotate them by restarting the auth service on a cron job, but that
would drop every active session. Rotation happens in place, and clients
refresh transparently.

After: Session tokens are rotated every 24 hours, in place, and clients
refresh transparently.
