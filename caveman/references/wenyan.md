# Wenyan Levels

Classical Chinese at the active level. Character reduction is 80-90 percent,
but characters are not tokens: CJK characters often cost more tokens each,
so verify savings for your tokenizer before adopting wenyan for economy; its
primary value is extreme visual terseness for Chinese-reading users.

| Level | What changes |
| --- | --- |
| **basic** | Semi-classical. Drop filler and hedging, keep grammar structure, classical register. |
| **full** | Fully classical wenyan. Classical sentence patterns, verbs precede objects, subjects often omitted, classical particles (之/乃/為/其). |
| **maximum** | Extreme abbreviation while keeping the classical feel. |

<examples for="wenyan" request="Why does my React component re-render?">
  <variant for="basic">組件頻重繪，以每繪新生對象參照故。以 useMemo 包之。</variant>
  <variant for="full">每繪新生對象參照，故重繪；以 useMemo 包之則免。</variant>
  <variant for="maximum">新參照則重繪。useMemo 包之。</variant>
</examples>
