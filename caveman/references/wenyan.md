# Wenyan Levels

Classical Chinese compression tiers. Character reduction is 80-90 percent,
but characters are not tokens: CJK characters often cost more tokens each,
so verify savings for your tokenizer before adopting wenyan for economy;
its primary value is extreme visual terseness for Chinese-reading users.

| Level | What changes |
|-------|--------------|
| **wenyan-lite** | Semi-classical. Drop filler and hedging, keep grammar structure, classical register. |
| **wenyan-full** | Fully classical wenyan. Classical sentence patterns, verbs precede objects, subjects often omitted, classical particles (之/乃/為/其). |
| **wenyan-ultra** | Extreme abbreviation while keeping the classical feel. Maximum compression. |

Rules:

- Classical characters belong to wenyan levels only; never swap a word for a classical character at other levels.
- Technical terms, code, API names, and error strings stay verbatim in any level.
- All core rules (negation preservation, exact numbers, auto-clarity) still apply.

<wenyan_examples request="Why does my React component re-render?">
  <wenyan_lite>組件頻重繪，以每繪新生對象參照故。以 useMemo 包之。</wenyan_lite>
  <wenyan_full>每繪新生對象參照，故重繪；以 useMemo 包之則免。</wenyan_full>
  <wenyan_ultra>新參照則重繪。useMemo 包之。</wenyan_ultra>
</wenyan_examples>
