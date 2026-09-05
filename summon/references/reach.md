# Reach

How a named skill gets into a delegate. Take the first variant that holds,
reading top down. The order is reliability of the text being read, not
cost: preloading spends tokens up front whether or not the skill is needed,
and buys certainty that the body is present.

| Variant | Holds when | What the brief does | Standing |
| --- | --- | --- | --- |
| Preloaded | the agent definition names the skill under `skills:`, so the body is injected at start | names the skill only | documented |
| Invocable | the delegate has a skill-loading tool | commands the skill by name in slash form; the delegate loads the body itself | measured |
| Readable | no skill tool, but the file is reachable on disk | gives the absolute path and says to read it before starting | measured |
| Definable | no preload exists, and the harness hot-reloads agent definitions | mints an agent definition naming the skill under `skills:`, then dispatches to that type | documented, untested: the agents directory must exist at session start, since the docs require a restart to pick one up |
| Sealed | none of the above holds | excerpts the binding rules into the brief's rules field | documented, not observed |

Measured for Invocable: the default general-purpose delegate and the
read-only explorer delegate both carried a skill tool and a 30-entry skill
listing, and both returned a full skill body on request; haiku and sonnet
each followed a bare slash pointer. Measured for Readable: the delegate
read the file, followed it to the level file it named, and complied.

Sealed arises when the skill tool is omitted from the delegate's tools or
listed among disallowed tools, when the skill is marked as not
model-invocable, or on a harness with no skill loading at all.

Point rather than paste wherever the delegate can load the skill itself:
the bare-pointer arm beat the full-dump arm on compliance and on cost.
Excerpting is the Sealed branch alone, under the excerpting law in
`dispatch`.

Where a harness preloads skills at all, it does so at agent-definition
time, and the prompt is the only call-time channel. That is what Definable
and Sealed exist for.

Probe rather than assume. An unfamiliar harness, or an agent definition
with a restricted tool list, settles in one probe delegate (procedure in
`harness`), one delegation that settles reach for every later one.
Pointing at a skill also leaves the evidence obligation intact: a
delegate that loaded a whole skill still went to the repository for the
value the skill told it to derive.
