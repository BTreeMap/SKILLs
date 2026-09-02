# Calibration: false positives and human details

Two lists: evidence that proves nothing alone, and writing to leave intact.

## What not to flag

A person may use some of these patterns. Treat no item below as proof by
itself:

- **Perfect grammar and consistent style.** Many writers are professionals or have been edited. Polish does not equal AI.
- **Mixed casual and formal styles.** This can reflect the writer's field, age, or personal habits.
- **"Bland" or "robotic" prose.** AI prose has specific tells. Generic dryness without those tells is just dry writing.
- **Formal or academic words.** Only the specific words §7 in `language` lists count as tells. Do not simplify every formal word.
- **Letter-style opening or closing on a comment.** Salutations and sign-offs predate ChatGPT by centuries.
- **Common transition words in isolation.** Additionally, moreover, consequently are AI-coded only when piled up. One however is not a tell.
- **Curly quotes alone.** macOS, Word, Google Docs, and most CMSes auto-curl by default. Curly quotes count only when stacked with other tells.
- **Em dashes alone.** Many editors and journalists use them often. Em dashes are evidence only when paired with formulaic sales-y rhythm.
- **One short sentence for emphasis.** Flag dramatic fragments only when several appear in a row.
- **Deliberate repeated openings.** Writers repeat an opening to build rhythm or pressure, as in "She came. She saw. She conquered." Change it only when the repetition adds nothing.
- **"Honestly" or "look" mid-sentence.** Ordinary in casual writing. The tell is the standalone theatrical opener, not the word itself.
- **Useful limits and disclaimers.** Keep scope statements, legal and safety notices, real corrections, named objections, replies, and FAQ answers.
- **Real alternatives.** Keep options a reader may consider in a design document, tutorial, or argument. Remove only an unlikely option the text dismisses and never uses again.
- **Unsourced claims.** Most of the web is unsourced. Lack of citations proves nothing.
- **Correct, complex formatting.** Visual editors and templates produce clean output without any AI.
- **Secondhand text.** Do not rewrite watched phrases inside quotations, titles, proper names, or examples where the phrase is discussed rather than used.
- **A single placement verb.** "The risk sits in the handoff" is ordinary English. §37 in `register` counts density; flag only above its threshold, and never an instance the writer's own sample uses.
- **Personification the writer chose.** Some writers personify systems as a signature move. A personal style file or sample that does so outranks §37 and the interiority case of §27; keep the voice and resolve the conflict in the writer's favor without asking.
- **A superlative the text earns.** After four numbers, "the largest" is a fact. §38 targets a ranking the writer never made; a comparison the reader can check stays.
- **First-person experience the writer has.** The first-person case of §5 targets invented observation doing a citation's job. Autobiography that the surrounding text supports stays.
- **A count the reader must hold.** The count case of §28 targets decoration; a count that helps the reader track items across intervening text is navigation.
- **Real terms of art and defined coinages.** Technical debt, scope creep, and a label the writer defines and then uses are vocabulary; the coined-label case of §32 targets an undefined label posing as one. A suffix match alone is weak: tax, debt, and trap are ordinary literal words.
- **Honest and honestly in dialogue or mid-sentence.** Quoted speech and a casual adverb stay. The honesty-qualifier case of §33 targets the writer marking their own claim as the honest one.
- **Even rhythm in a list, a spec, or a table caption.** Enumerations and reference entries are uniform by design. §36 measures running prose, one block of about 40 sentences at a time, against the writer's own baseline when a sample exists.
- **Jargon the audience shares.** A noun stack in a message between two engineers who share the context is compression that works. §39 targets the same register reaching a reader who lacks the context.
- **A rule the format needs.** Front matter delimiters, a required thematic break, and a rule inside a template stay; §18 targets rules between sections that headings already separate.
- **Claude-favored words in isolation.** Genuine, latent, settled, seam, and quietly are everyday words. §7 counts them only in a cluster.
- **Corrections in a document about change.** A changelog, a review, or an erratum states what was wrong; §40 targets the checking voice inside a document that is presenting a finding.

Weigh hits by the signal strength the index states. A word list applied as
a ban flattens prose: it removes ordinary English, and a suppressed term
tends to resurface. Rewrite the sentence around its point; a word swap
leaves the shape.

When unsure, look for several patterns together. One em dash proves nothing.
Several stock patterns in the same passage are stronger evidence.

## Human details to keep

These often carry the writer's voice. Keep them unless they hurt the meaning:

- **Specific, unusual details.** A real address, an odd quote, a phrase such as "the lawyer who used to work upstairs from my dentist."
- **Mixed feelings and unresolved tension.** Lines such as "I think this is mostly good, but it bothers me, and I can't fully explain why."
- **Dated, era-bound references.** Slang, memes, or in-jokes that map to a specific year and subculture. Models lag by a year or more.
- **Deliberate first-person choices.** A cut or word choice the writer can explain.
- **Variety in sentence length.** Real writing alternates short and long. AI writing tends toward an even, mid-length cadence.
- **Genuine asides, parentheticals, self-corrections.** "(I keep wanting to say 'almost' here, but it really was certain.)" Models rarely interrupt themselves like this.
- **Edits made before November 30, 2022.** ChatGPT's public launch. Anything older is, with very rare exceptions, not AI-written.
