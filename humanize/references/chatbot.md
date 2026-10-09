# Chatbot patterns (§20-22)

### 20. Chatbot text left in the answer

**Watch:** I hope this helps, Of course!, Certainly!, You're absolutely
right!, Would you like..., Want me to...?, Want me to give examples?, Should
I continue?, let me know, here is a...

**Problem:** Chatbot's greeting, offer, or closing remains in standalone
text.

**Exceptions:** Letter-style opening or closing on comment. Salutations and
sign-offs predate ChatGPT by centuries.

**Example**

Before: Here is an overview of the French Revolution. I hope this helps! Let
me know if you'd like me to expand on any section.

After: The French Revolution began in 1789 when financial crisis and food
shortages led to widespread unrest.

### 21. Knowledge-limit disclaimers and guesses

**Watch:** as of [date], Up to my last training update, While specific
details are limited/scarce..., based on available information, not publicly
available, maintains a low profile, keeps personal details private, prefers
to stay out of the spotlight, likely [grew up/studied/began], it is believed
that

**Problem:** Model mentions its knowledge cutoff, or explains it found no
source, then fills gap with plausible guess. State what source does not
show, or remove sentence. Never present guess as fact.

**Example: cutoff disclaimer**

Before: While specific details about the company's founding are not
extensively documented in readily available sources, it appears to have been
established sometime in the 1990s.

After: The company's founding date is not documented in the available
sources. (Or cut the sentence. State a date only if a source provides one.)

**Example: speculative gap-fill**

Before: Information about her early life is not publicly available,
suggesting she maintains a low profile and keeps personal details private.
She likely grew up in a middle-class household, which shaped her later
interest in education reform.

After: Her early life is not documented in the available sources. (Or omit
the section.)

### 22. Overly agreeable tone

**Problem:** Praise or agreement before answer.

**Example**

Before: Great question! You're absolutely right that this is a complex
topic. That's an excellent point about the economic factors.

After: The economic factors you mentioned are relevant here.
