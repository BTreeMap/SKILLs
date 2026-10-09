# Caveman Help Verb

Display quick-reference card built from spine, written in caveman style.
Write no file, persist nothing, change no level.

Build card from these sections, in this order:

1. Levels: one row per row of spine's Intensity table: level, its trigger,
   what changes. Trigger is `/caveman <level>`; `/caveman` alone selects
   full, the default. Close section with: level sticks until changed or
   session end.
2. Verbs: one row per row of spine's Verbs table: verb, its trigger, what it
   does. Trigger is `/caveman <verb>`, and `/caveman refactor <file>` for
   refactor. Note verbs are one-shot reports, leave active level untouched.
3. Language: reply keeps user's language, so Portuguese input gets
   Portuguese caveman reply; style compresses, language does not. Technical
   terms, code, commands, exact error strings stay verbatim unless user asks
   for translation.
4. Deactivate: say "stop caveman" or "normal mode"; resume anytime with
   `/caveman`.
5. Source: levels and verbs defined in this skill, adapted from upstream
   caveman project: https://github.com/JuliusBrussee/caveman
