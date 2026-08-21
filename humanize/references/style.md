# Style patterns (§14-19)

Typography and formatting: dashes, bold, headings, emoji, quote marks. All
mechanically checkable by searching the text. Routing cues live in the
detection index; this file owns the rules, problems, and examples.

### 14. Em and en dashes

**Rule:** The final rewrite must not contain an em dash (U+2014) or an en dash
(U+2013) unless the writer's sample uses them; then match the sample's rate.
Replace each with a period, comma, colon, or parentheses, or rewrite the
sentence. Also catch a spaced hyphen and a double hyphen used as dashes. The
example below uses the en dash and double-hyphen forms; the em dash behaves
identically.
<before>
The term is primarily promoted by Dutch institutions – not by the people themselves. The changes -- long overdue according to critics -- will take effect immediately.
</before>
<after>
The term is primarily promoted by Dutch institutions, not by the people themselves. The changes, long overdue according to critics, will take effect immediately.
</after>

Before returning the rewrite, search for U+2014 and U+2013. Remove each one
unless the writer's sample uses that mark.

### 15. Too much bold text

**Problem:** Words and phrases bolded without a clear reason.
<before>
It blends **OKRs (Objectives and Key Results)**, **KPIs (Key Performance Indicators)**, and visual strategy tools such as the **Business Model Canvas (BMC)** and **Balanced Scorecard (BSC)**.
</before>
<after>
It blends OKRs, KPIs, and visual strategy tools like the Business Model Canvas and Balanced Scorecard.
</after>

### 16. Lists with bold mini-headings

**Problem:** Vertical lists in which every item starts with a bold label and a colon.
<before>
- **User Experience:** The user experience has been significantly improved with a new interface.
- **Performance:** Performance has been enhanced through optimized algorithms.
- **Security:** Security has been strengthened with end-to-end encryption.
</before>
<after>
The update improves the interface, speeds up load times through optimized algorithms, and adds end-to-end encryption.
</after>

### 17. Title case in headings

**Problem:** Every main word of a heading capitalized.
<before>
## Strategic Negotiations And Global Partnerships
</before>
<after>
## Strategic negotiations and global partnerships
</after>

### 18. Emojis

**Problem:** Emojis added to headings and list items as decoration.
<before>
🚀 **Launch Phase:** The product launches in Q3
💡 **Key Insight:** Users prefer simplicity
✅ **Next Steps:** Schedule follow-up meeting
</before>
<after>
The product launches in Q3. User research showed a preference for simplicity. Next step: schedule a follow-up meeting.
</after>

### 19. Curly quotation marks

**Problem:** Curly quotes (“...”) where the writer or target format uses straight quotes ("...").
<before>
He said “the project is on track” but others disagreed.
</before>
<after>
He said "the project is on track" but others disagreed.
</after>
