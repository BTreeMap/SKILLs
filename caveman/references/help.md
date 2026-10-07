# Caveman Help Verb

Display a quick-reference card built from the spine, written in caveman
style. Write no file, persist nothing, and change no level.

Build the card from these sections, in this order:

1. Levels: one row per row of the spine's Intensity table, giving the level,
   its trigger, and what changes. The trigger is `/caveman <level>`;
   `/caveman` alone selects full, the default. Close the section with: level
   sticks until changed or session end.
2. Verbs: one row per row of the spine's Verbs table, giving the verb, its
   trigger, and what it does. The trigger is `/caveman <verb>`, and
   `/caveman refactor <file>` for refactor. Note that verbs are one-shot
   reports and leave the active level untouched.
3. Language: the reply keeps the user's language, so Portuguese input gets a
   Portuguese caveman reply; style compresses, language does not. Technical
   terms, code, commands, and exact error strings stay verbatim unless the
   user asks for translation.
4. Deactivate: say "stop caveman" or "normal mode"; resume anytime with
   `/caveman`.
5. Source: levels and verbs are defined in this skill, adapted from the
   upstream caveman project: https://github.com/JuliusBrussee/caveman
