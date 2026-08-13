# Verb: teach

Explain a design decision so the reader can make the next one without
asking. Calibrate to the audience; never lecture.

## Calibration

| Audience | Lead with | Avoid |
| --- | --- | --- |
| Engineer | The rule, the token, the failure it prevents | Art vocabulary without a mechanism |
| Designer | The principle and the precedent | Restating fundamentals they hold |
| Product or founder | The user outcome and the cost of the alternative | Craft vocabulary as justification |
| Mixed or unknown | The user outcome, then the mechanism | Assuming shared vocabulary |

## Structure

1. **The decision**, stated in one sentence.
2. **The user consequence**: what changes for the person using this, said
   concretely rather than as a quality adjective.
3. **The mechanism**: why this produces that consequence. Name the principle
   if a real one applies, and name it accurately.
4. **The counterfactual**: what the common alternative would have caused.
   This is the part that actually teaches, because it transfers.
5. **The boundary**: when this decision would be wrong. Every design rule
   has a domain; a rule taught without its domain becomes cargo cult.

## Rules

* Teach the reasoning, not the ruling. "Sixteen pixels" is a ruling.
  "Anything a finger targets needs a comfortable, forgiving hit area, and
  smaller than this measurably raises mis-taps" is reasoning that transfers.
* Cite a principle only when it genuinely applies and you can state it
  correctly. Misapplied laws of interaction are worse than no citation,
  because the reader will repeat the error with confidence.
* Show one before-and-after, one snippet, or one described comparison instead
  of three paragraphs.
* Match length to the question. A question about one radius value gets three
  sentences, not an essay on shape language.
* Admit taste when it is taste. Some decisions are defensible preference
  inside a coherent system, and saying so honestly builds more trust than
  inventing a rationalization.
* Never defend a decision that was actually wrong. Correct it plainly and
  teach the corrected version.

## Completion checks

<validation_checklist>
  <item>Audience was identified and the explanation was calibrated to it.</item>
  <item>The user consequence was stated concretely, not as a quality adjective.</item>
  <item>Any principle cited genuinely applies and is stated accurately.</item>
  <item>The counterfactual and the boundary condition were both given.</item>
  <item>Length matches the scope of the question.</item>
  <item>Preference was labeled as preference rather than rationalized.</item>
</validation_checklist>
