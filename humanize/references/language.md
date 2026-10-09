# Language and grammar patterns (§7-13)

### 7. Overused AI words

**Watch:** Actually, additionally, align with, crucial, delve, emphasizing,
enduring, enhance, fostering, garner, gate/gated/gating (figurative;
preserve established technical usage), genuine/genuinely, highlight (verb),
interplay, intricate/intricacies, key (adjective), landscape (abstract
noun), latent, pivotal, quietly, seam (figurative), settled (figurative),
showcase, tapestry (abstract noun), testament, underscore (verb), valuable,
vibrant

**Problem:** AI writing uses these words far more often than people do,
especially in groups. Count cluster, never single word; placement metaphors
such as load-bearing belong to §37 in `register`.

**Exceptions:**

- Formal or academic words. Only words listed above count as tells. Do not
  simplify every formal word.
- Common transition words in isolation. Additionally, moreover, consequently
  are AI-coded only when piled up. One however is not a tell.
- Claude-favored words in isolation. Genuine, latent, settled, seam, quietly
  are everyday words.

<examples>
  <example>
    <before>Additionally, a distinctive feature of Somali cuisine is the incorporation of camel meat. An enduring testament to Italian colonial influence is the widespread adoption of pasta in the local culinary landscape, showcasing how these dishes have integrated into the traditional diet.</before>
    <after>Somali cuisine also includes camel meat, which is considered a delicacy. Pasta dishes, introduced during Italian colonization, remain common, especially in the south.</after>
  </example>
</examples>

### 8. Avoiding is and are

**Watch:** serves as/stands as/marks/represents [a], boasts/features/offers
[a]

**Problem:** Simple verbs such as is, are, has replaced with longer phrases.

<examples>
  <example>
    <before>Gallery 825 serves as LAAA's exhibition space for contemporary art. The gallery features four separate spaces and boasts over 3,000 square feet.</before>
    <after>Gallery 825 is LAAA's exhibition space for contemporary art. The gallery has four rooms totaling 3,000 square feet.</after>
  </example>
</examples>

### 9. Not X but Y and clipped negative endings

**Problem:** Overused "Not only...but..." and "It's not just X, it's Y"
frames, clipped endings such as "no guessing" where clear clause belongs,
staccato negation. Staccato form carries no "not just", so scan for phrase
misses it: watch for two or more sentences in a row beginning with No or Not
a. Cutting negated half can change what sentence claims; apply invariant 5.

<examples>
  <example>
    <before>It's not just about the beat riding under the vocals; it's part of the aggression and atmosphere. It's not merely a song, it's a statement.</before>
    <after>The heavy beat adds to the aggressive tone.</after>
  </example>
  <example for="tailing negation">
    <before>The options come from the selected item, no guessing.</before>
    <after>The options come from the selected item without forcing the user to guess.</after>
  </example>
  <example for="staccato negation">
    <before>No config file. No daemon. No surprises. Just a binary.</before>
    <after>It ships as one binary and needs no config file or daemon.</after>
  </example>
</examples>

### 10. Forced groups of three

**Problem:** Ideas forced into triads to sound complete.

<examples>
  <example>
    <before>The event features keynote sessions, panel discussions, and networking opportunities. Attendees can expect innovation, inspiration, and industry insights.</before>
    <after>The event includes talks and panels. There's also time for informal networking between sessions.</after>
  </example>
</examples>

### 11. Changing names and repeating sentence openings

**Problem:** Repetition handled by rule instead of by ear: same person or
thing keeps getting renamed, or several sentences open with same subject,
often she or he. One clear name for one subject. Repeated openings: merge
sentences, change subject when that helps, or begin with action. Fix
repeated sentence pattern, not repeated word: remaining sentence may still
start with "She."

**Exceptions:** Deliberate repeated openings. Writers repeat opening to
build rhythm or pressure, as in "She came. She saw. She conquered." Change
only when repetition adds nothing.

<examples>
  <example for="synonym cycling">
    <before>The protagonist faces many challenges. The main character must overcome obstacles. The central figure eventually triumphs. The hero returns home.</before>
    <after>The protagonist faces many challenges but eventually triumphs and returns home.</after>
  </example>
  <example for="repeated openings">
    <before>She noted the door. She noted the lock on it. She filed both away.</before>
    <after>She noted the door and its lock, then filed both away.</after>
  </example>
</examples>

### 12. False from X to Y ranges

**Problem:** "from X to Y" where X and Y do not form a real range.

<examples>
  <example>
    <before>Our journey through the universe has taken us from the singularity of the Big Bang to the grand cosmic web, from the birth and death of stars to the enigmatic dance of dark matter.</before>
    <after>The book covers the Big Bang, star formation, and current theories about dark matter.</after>
  </example>
</examples>

### 13. Passive voice and missing subjects

**Problem:** Actor hidden or subject dropped. Use active voice when it makes
actor and action clearer.

<examples>
  <example>
    <before>No configuration file needed. The results are preserved automatically.</before>
    <after>You do not need a configuration file. The system preserves the results automatically.</after>
  </example>
</examples>
