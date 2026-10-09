# Style patterns (§14-19)

### 14. Em and en dashes

**Rule:** Final rewrite must not contain em dash (U+2014) or en dash
(U+2013) unless writer's sample uses them; then match sample's rate. Replace
each with period, comma, colon, or parentheses, or rewrite sentence. Also
catch spaced hyphen and double hyphen used as dashes. Example below uses en
dash and double-hyphen forms; em dash behaves identically.

As evidence, em dashes count only when paired with formulaic sales-y rhythm;
many editors and journalists use them often.

**Example**

Before: The term is primarily promoted by Dutch institutions – not by the
people themselves. The changes -- long overdue according to critics -- will
take effect immediately.

After: The term is primarily promoted by Dutch institutions, not by the
people themselves. The changes, long overdue according to critics, will take
effect immediately.

### 15. Too much bold text

**Problem:** Words and phrases bolded without clear reason.

**Example**

Before:

```markdown
It blends **OKRs (Objectives and Key Results)**, **KPIs (Key Performance Indicators)**, and visual strategy tools such as the **Business Model Canvas (BMC)** and **Balanced Scorecard (BSC)**.
```

After: It blends OKRs, KPIs, and visual strategy tools like the Business
Model Canvas and Balanced Scorecard.

### 16. Lists with bold mini-headings

**Problem:** Vertical lists where every item starts with bold label and
colon.

**Example**

Before:

```markdown
- **User Experience:** The user experience has been significantly improved with a new interface.
- **Performance:** Performance has been enhanced through optimized algorithms.
- **Security:** Security has been strengthened with end-to-end encryption.
```

After: The update improves the interface, speeds up load times through
optimized algorithms, and adds end-to-end encryption.

### 17. Title case in headings

**Problem:** Every main word of heading capitalized.

**Example**

Before:

```markdown
## Strategic Negotiations And Global Partnerships
```

After:

```markdown
## Strategic negotiations and global partnerships
```

### 18. Emojis and decorative rules

**Problem:** Emojis added to headings and list items as decoration;
horizontal rules (`---`) placed between sections where heading or paragraph
break already separates them.

**Exceptions:** Front matter delimiters, required thematic break, rule
inside template.

**Example**

Before:

```markdown
🚀 **Launch Phase:** The product launches in Q3
💡 **Key Insight:** Users prefer simplicity
✅ **Next Steps:** Schedule follow-up meeting
```

After: The product launches in Q3. User research showed a preference for
simplicity. Next step: schedule a follow-up meeting.

**Example: rules as dividers**

Before:

```markdown
## Setup

Install the package.

---

## Usage

Run the command.
```

After:

```markdown
## Setup

Install the package.

## Usage

Run the command.
```

### 19. Curly quotation marks

**Problem:** Curly quotes (“...”) where writer or target format uses
straight quotes ("...").

As evidence, curly quotes count only when stacked with other signs; macOS,
Word, Google Docs, and most CMSes auto-curl by default.

**Example**

Before: He said “the project is on track” but others disagreed.

After: He said "the project is on track" but others disagreed.
