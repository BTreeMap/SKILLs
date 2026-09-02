# Literature review: what are the main methodological approaches to thematic analysis, and how do they differ in procedure, epistemological commitments, and quality criteria?

## Summary

The included literature describes a family of pattern-finding procedures that share a vocabulary and disagree about what
a code is, what a theme is, and whether coding can be correct. Four positions
recur: an approach organised around coding accuracy and multiple coders; an
approach organised around a shared codebook applied by a team; an approach
that treats the analyst's interpretation as the instrument and rejects
accuracy as a standard; and a set of matrix-based procedures that trade
interpretive depth for auditability across many cases. These positions carry
incompatible quality criteria, so a procedure borrowed from one and a
justification borrowed from another produces work that satisfies neither.
The sharpest live disagreement is whether agreement between coders evidences
anything; the corpus contains both a worked procedure for measuring it and an
argument that measuring it misdescribes what qualitative analysis does. For
the data this review was asked to target (user feedback, bug tickets, and
other high-volume operational text), the computing literature in the corpus
has largely pursued automated classification into fixed categories, leaving
theme development aside, so the two literatures address different problems and
the corpus does not contain a study that reconciles them.

## Method

Searches ran on 2026-08-28 against OpenAlex (31 queries), Crossref (7
queries), and six OpenAlex snowball rounds (backward and forward) seeded from
Braun & Clarke 2006 [6], McDonald et al. 2019 [22], and Gale et al. 2013
[11]. That date is the review's as-of point. Every query was logged by the
session script; all searches returned truncated result sets against upstream
totals in the thousands to millions, so coverage is a relevance-ranked sample
rather than an enumeration of the field.

Criteria were fixed before the first search. Inclusion required a
methodological contribution to thematic analysis: proposing, codifying,
critiquing, or comparing a named approach, its procedure, or its quality
criteria. One amendment was recorded mid-review, after the requester
specified that the target application is user feedback and HCI-style
qualitative data rather than psychology-default methodology. The amendment
added an inclusion criterion for methodologically reflective work on user
feedback, tickets, app reviews, and HCI, CSCW, or software-engineering
qualitative data, and triggered a further search round and a full re-screen
under the amended criteria.

| Flow | N |
| --- | --- |
| Records identified and deduplicated into the corpus | 574 |
| Excluded at title/abstract screening | 537 |
| Included | 37 |
| Included at full-text read level | 3 |
| Included at abstract read level | 34 |

The largest exclusion categories were general qualitative-methods material
with no distinct contribution to thematic analysis (190), substantive
empirical studies with no methodological commentary (67 plus 27 applications
of thematic analysis and 24 domain studies), and term collisions where
"analysis", "taxonomy", or "classification" matched natural-science and
algorithmic work (38). Seven of the 37 included papers entered through the
snowball rounds rather than keyword search, concentrated in the intercoder
reliability and rapid-analysis strands.

## Thematic analysis names a family of methods

The corpus's organising claim is that approaches sharing the name differ
enough to be separate methods. Braun & Clarke [25] set out a typology of
pattern-based approaches that separates coding reliability, codebook,
reflexive, and thematic coding variants, and cut it across a distinction
between small-q work operating inside a (post)positivist frame and big-Q work
that does not. Their stated aim in that paper is informed selection among
methods.

The corpus supports the descriptive claim that the schools coexist, from
independent author groups. Boyatzis [3] presents thematic analysis as a way
of moving between qualitative and quantitative traditions, with codes
developed systematically and checked for reliability. Guest et al. [8]
present an applied variant built on codebooks and structured team coding.
Aronson [2], writing before any of these, describes a deliberately loose
procedure of collecting data, identifying patterns, and combining them into
themes, which is evidence that the name covered an informal practice before
it was codified. Braun & Clarke [6] then codified a six-phase version that
the rest of the corpus positions itself against.

The stronger claim, that the schools are mutually incompatible, comes
predominantly from one author group. Braun & Clarke argue it
across four included papers [19][25][26][32], and their argument that generic
quality checklists misjudge reflexive thematic analysis [26] is an untested
position statement. Independent support in this corpus is
indirect and comes from one paper: Stol et al. [15] diagnose the same failure
mode in software engineering, where a method is named in a paper without its
procedure being followed. They reach that conclusion about grounded theory,
so it corroborates the pattern while the specific claim about thematic
analysis stays uncorroborated.

Reading level constrains this section. Braun & Clarke's typology [25] and the
six-phase procedure [6] were both extracted at abstract level with the
procedural detail taken from publisher records and secondary methodological
summaries, because the primary texts were paywalled in this environment.

## Where the schools differ: the code, the theme, and who decides

The corpus locates the disagreement in three places.

What a code is. In the coding-reliability and codebook lineages a code is a
label whose application can be right or wrong, which is what makes agreement
measurable. O'Connor & Joffe [27], read at full text, build an eight-step
procedure on that premise and recommend a maximum of 30 to 40 codes, and
preferably 20 or fewer. In the reflexive account a code is an analytic
product of the researcher's engagement, so accuracy is not defined for it
[19][25].

What a theme is. Attride-Stirling [4] treats themes as tiers to be
constructed and displayed: Basic themes cluster into Organizing themes, which
resolve into a Global theme, with practical guidance of roughly 5 to 14
groupings per network and a caution that the networks are a tool within the
analysis, never its whole. Braun & Clarke [32] distinguish themes as
shared patterns of meaning from topic summaries that merely group everything
said about a subject, and treat the latter as a common failure. Vaismoradi et
al. [10] and Vaismoradi & Snelgrove [23] locate a related boundary between
thematic analysis and qualitative content analysis, turning on whether
counting codes is admissible and on what "theme" denotes.

Whether prior structure is allowed. Fereday & Muir-Cochrane [5], read at full
text, run a hybrid in six stages: develop a code manual from theory, test its
reliability with a second coder, summarise the data, apply the template while
letting data-driven codes emerge, cluster codes into themes, and corroborate
those themes against the original data. Their own case shows the mechanism:
a code for "trust and respect" began nested inside a theory-derived category
and was promoted to a separate data-driven code. Template analysis [9][12]
formalises the same move differently: an initial template, often carrying a
priori themes, built on a subset of data and then revised iteratively against
the whole. Proudfoot [33] sequences inductive and deductive passes within
mixed methods designs. These procedures are incompatible with the reflexive
position that themes are constructed by the analyst, never found against a
prior frame,
and the corpus does not contain a study that tests which produces better
analyses.

## Multiple coders and reliability: the corpus's sharpest disagreement

Both sides are represented by independent author groups, and the corpus does
not resolve the disagreement.

O'Connor & Joffe [27] give the affirmative case its operational form:
decide coder count, data proportion, coding unit, code depth, statistic, and
threshold in advance; build the frame through immersion; have a second coder
work an independently prepared subset; compute per-code reliability; discuss
and refine; then apply the final frame. They recommend double-coding 10 to
25% of data units and report the conventional interpretive bands, with values
above 0.9 acceptable to all and above 0.8 acceptable to many, citing the
Landis & Koch scale. They also name where it does not belong: recursive
designs such as grounded theory, purely exploratory work, and analyses
prioritising depth over consistency. Their own framing limits the claim:
"ICR is never an end in itself; it is merely a means to the ultimate goal of
achieving an insightful and robust qualitative analysis." MacPhail et al.
[13] supply a second, independent set of process guidelines, and Artstein &
Poesio [7] supply the statistical treatment of agreement coefficients from
computational linguistics.

Braun & Clarke [19][25][26] hold the opposing position, that agreement
between coders cannot evidence quality where coding is interpretive, so
reporting it alongside a reflexive procedure misdescribes what was done.

McDonald et al. [22] is the corpus's empirical contribution to this
disagreement and the one paper addressed directly to computing practice.
Their meta-analysis of CSCW and HCI papers from 2016 to 2018 reports that
inter-rater reliability appears in roughly one in nine qualitative papers,
and they argue the field needs epistemology-specific reporting norms, and
no blanket rule. That paper was read at abstract
level here; the one-in-nine figure comes from its abstract and indexed
summaries. Díaz et al. [34] apply agreement
measures within collaborative software-engineering studies, which shows the
practice has an applied-computing constituency independent of the health and
psychology literatures.

## Matrix and template procedures for team and high-volume settings

A distinct group of included papers trades interpretive depth for
auditability across cases, which is the property that matters when many
records must be handled by more than one person.

Gale et al. [11], read at full text, set out the Framework Method in seven
stages: transcription, familiarisation, coding, developing a working
analytical framework, applying that framework, charting into a matrix whose
rows are cases and columns are codes, and interpretation. The matrix is the
mechanism: it reduces volume while keeping each case's context and retains
quotation references for illustration. They recommend that at least two
researchers, or one from each discipline in a multidisciplinary team,
independently code the first few transcripts where feasible. They also state
the method's boundary condition plainly: "The Framework Method cannot
accommodate highly heterogeneous data, i.e. data must cover similar topics or
key issues so that it is possible to categorize it." Two further included
papers [14][30] describe the same method in applied use. Miles & Huberman [1]
are the corpus's earlier statement of the underlying idea, that data
reduction and data display are analytic operations.

A rapid-analysis strand pushes further in the same direction, replacing
line-by-line coding with templated summaries and matrix displays to reach
decision-makers on compressed timelines [18][21][28][31]. Saunders et al.
[36] make the team-facing case explicitly, arguing that practical guidance
for non-specialists is sparse and that non-specialist perspectives can enrich
interpretation. The corpus leaves comparability with in-depth analysis
open: Taylor et al. [18] and Gale et al. [21] each
compare rapid against fuller analysis in a single applied setting, which is
not enough to establish equivalence in general, and all four rapid-analysis
papers were read at abstract level here.

## Analysis of user feedback in computing has developed separately

The included computing papers on user feedback do something different from
the thematic analysis literature. Dąbrowski et al. [35] survey app-review
analysis for software engineering, Wang et al. [24] map crowdsourced
requirements engineering built on user feedback, and Lu & Liang [17]
classify non-functional requirements from app reviews. The work in this
strand is oriented toward assigning high volumes of feedback to predefined
categories such as bug report, feature request, or requirement type. Theme
development, in the sense the thematic analysis literature uses, is not the
objective. Both [35] and [24] are surveys, so their characterisations of
individual primary studies are reported here as those surveys' accounts of
the underlying studies.

None of the 37 included papers evaluates a thematic analysis procedure on
bug tickets, issue trackers, or support transcripts, and none compares
interpretive theme development against category classification on the same
feedback corpus. The two literatures in this corpus meet only at McDonald et
al. [22] and the software-engineering reliability and grounded-theory work
[15][34][37], all of which concern researchers' qualitative practice, none the
reading of product feedback.

## Mapping onto a thematic analysis skill

This section is design guidance derived from the synthesis, beyond what
the literature finds.

The corpus's central implication for a skill is that "do a thematic analysis"
is underspecified. A skill that emits one procedure will produce work whose
method and whose justification come from different schools, which is the
failure Braun & Clarke [32] and, for a different method, Stol et al. [15]
both describe. The first move should be selecting an approach, and the
selection should be recorded.

| Approach | Corpus records | Fits when | Quality standard it answers to |
| --- | --- | --- | --- |
| Reflexive | [6][19][25][26][29][32] | Open question, one analyst or a genuinely collaborative pair, meaning matters more than counts | Reflexivity and coherence of interpretation; agreement statistics are rejected |
| Codebook / coding reliability | [3][7][8][13][22][27][34] | Several people must code consistently; results feed a decision | Documented codebook, declared agreement procedure and threshold |
| Template | [9][12] | A working taxonomy exists and should evolve | Template versioning and revision history |
| Framework / matrix | [1][11][14][30] | Many cases, comparison across them, mixed-expertise team | Auditable matrix; requires reasonably homogeneous data [11] |
| Rapid / templated summary | [18][21][28][31][36] | Deadline-bound triage feeding a decision | Explicit statement of what depth was traded away |
| Hybrid inductive/deductive | [5][33] | Prior categories exist but must not foreclose new ones | Both passes documented; promotion of codes traceable [5] |

Concrete defaults the corpus supplies, so a skill invents none: double-code 10 to 25% of units when running an agreement
check, keep the codebook to 20 to 40 codes, and fix coder count, unit,
statistic, and threshold before coding starts, all from O'Connor & Joffe
[27]; aim for roughly 5 to 14 theme groupings, from Attride-Stirling [4];
have at least two people independently code the first few records in a
multidisciplinary team, from Gale et al. [11]. Each of these is one source's
recommendation, and [27] and [11] were read at full text while [4] was not.

Behaviours the corpus warrants a skill guarding against: reporting agreement
statistics alongside a reflexive procedure [19][25][26]; producing topic
summaries and calling them themes [32]; invoking saturation as a sample-size
rationale for interpretive work, which Braun & Clarke [20] argue is
incoherent because meaning is generated in analysis; and pushing
heterogeneous material through a matrix method whose stated precondition is
topical similarity [11].

For feedback and ticket data specifically, the corpus offers no validated
procedure, so a skill should present that as its own adaptation, with no validated
method behind it. The framework and rapid strands are the closest
structural fit, since tickets are many, short, and comparable across cases,
and the computing strand [17][24][35] indicates that the volume problem is
usually solved by classification into fixed categories, which is a different
operation with different failure modes.

## Limitations of this review

Read level is the main limitation. Only 3 of 37 included papers were read at
full text: Fereday & Muir-Cochrane [5], Gale et al. [11], and O'Connor &
Joffe [27]. Publisher access controls blocked full text for the rest,
including every Braun & Clarke paper, which is the corpus's most-cited author
group and the source of its organising typology. Procedural detail for
Braun & Clarke [6][25] and Attride-Stirling [4] was obtained from publisher
records and secondary methodological summaries. That is weaker than reading
the primary text, and those step lists should be checked against the
originals before they are hard-coded into a skill.

Coverage limits. Every logged search was truncated against upstream totals,
so the corpus is a relevance-ranked sample. Nowell et al.'s 2017 paper on
trustworthiness criteria for thematic analysis, which is frequently cited in
this area, was not retrieved by any query and is therefore absent from the
corpus and uncited here. Books are indexed unevenly: Boyatzis [3] carries no
DOI and entered under a title key, and Miles & Huberman [1] carries a journal
venue in its record that is an indexing artefact.

One verification flag was not cleared. The record at [16] resolves through a
DOI redirect to a Springer reissue, and its Crossref title match is 0.33
because the corpus holds a chapter title against a book-level record. I could
not reach the landing page to confirm the item, found no retraction
indication, and have therefore kept it in the bibliography without citing it
for any claim.

Screening was carried out by pattern rules applied to titles and keys with a
recorded reason for each of the 537 exclusions, rather than by reading every
abstract. That is faster and less accurate than abstract-level screening, and
it will have excluded some eligible papers whose titles did not signal a
methodological contribution. One such case is visible in the state file: a
critical review of how reflexive thematic analysis is reported in Health
Promotion International (doi:10.1093/heapro/daae049) was excluded by the
default rule although it plausibly satisfies the inclusion criterion. It is
named here without citation because it is in the excluded set. A
re-screen at abstract level would likely recover it and other papers like it,
and would strengthen the independent evidence available for the section on
whether the schools are incompatible.

## Gaps and open questions

None of the 37 included papers applies or evaluates a thematic analysis
procedure on bug tickets, issue-tracker data, or support transcripts.

None compares interpretive theme development against automated category
classification on the same body of user feedback, so the corpus cannot say
what the classification-oriented computing work [17][24][35] gives up.

The reliability disagreement rests on position statements on one side
[19][25][26] and procedural guidance on the other [13][27], with one
descriptive meta-analysis of reporting practice [22]. No included paper tests
whether measuring agreement changes the quality of the resulting analysis.

Rapid and templated analysis is compared against fuller analysis in two
single-setting studies [18][21]. Whether the reduction is safe in general,
and for which decisions, is not established by this corpus.

Claims that the schools are mutually incompatible come predominantly from one
author group across four included papers [19][25][26][32]; independent
corroboration in the corpus is indirect [15].

## Included papers

| # | Authors | Year | Title | Venue | Read level | DOI / key |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Miles & Huberman | 1994 | Qualitative Data Analysis: An Expanded Sourcebook | (book; record venue is an indexing artefact) | abstract | [10.1016/s0272-4944(05)80231-2](https://doi.org/10.1016/s0272-4944(05)80231-2) |
| 2 | Aronson | 1995 | A Pragmatic View of Thematic Analysis | The Qualitative Report | abstract | [10.46743/2160-3715/1995.2069](https://doi.org/10.46743/2160-3715/1995.2069) |
| 3 | Boyatzis | 1998 | Transforming Qualitative Information: Thematic Analysis and Code Development | Sage (book) | abstract | no DOI; title key |
| 4 | Attride-Stirling | 2001 | Thematic networks: an analytic tool for qualitative research | Qualitative Research | abstract | [10.1177/146879410100100307](https://doi.org/10.1177/146879410100100307) |
| 5 | Fereday & Muir-Cochrane | 2006 | Demonstrating Rigor Using Thematic Analysis: A Hybrid Approach of Inductive and Deductive Coding and Theme Development | International Journal of Qualitative Methods | full-text | [10.1177/160940690600500107](https://doi.org/10.1177/160940690600500107) |
| 6 | Braun & Clarke | 2006 | Using thematic analysis in psychology | Qualitative Research in Psychology | abstract | [10.1191/1478088706qp063oa](https://doi.org/10.1191/1478088706qp063oa) |
| 7 | Artstein & Poesio | 2008 | Inter-Coder Agreement for Computational Linguistics | Computational Linguistics | abstract | [10.1162/coli.07-034-r2](https://doi.org/10.1162/coli.07-034-r2) |
| 8 | Guest, MacQueen & Namey | 2012 | Applied Thematic Analysis | Sage (book) | abstract | [10.4135/9781483384436](https://doi.org/10.4135/9781483384436) |
| 9 | King | 2012 | Doing Template Analysis | Qualitative Organizational Research | abstract | [10.4135/9781526435620.n24](https://doi.org/10.4135/9781526435620.n24) |
| 10 | Vaismoradi, Turunen & Bondas | 2013 | Content analysis and thematic analysis: Implications for conducting a qualitative descriptive study | Nursing and Health Sciences | abstract | [10.1111/nhs.12048](https://doi.org/10.1111/nhs.12048) |
| 11 | Gale, Heath, Cameron et al. | 2013 | Using the framework method for the analysis of qualitative data in multi-disciplinary health research | BMC Medical Research Methodology | full-text | [10.1186/1471-2288-13-117](https://doi.org/10.1186/1471-2288-13-117) |
| 12 | Brooks, McCluskey, Turley & King | 2015 | The Utility of Template Analysis in Qualitative Psychology Research | Qualitative Research in Psychology | abstract | [10.1080/14780887.2014.955224](https://doi.org/10.1080/14780887.2014.955224) |
| 13 | MacPhail et al. | 2015 | Process guidelines for establishing Intercoder Reliability in qualitative studies | Qualitative Research | abstract | [10.1177/1468794115577012](https://doi.org/10.1177/1468794115577012) |
| 14 | Parkinson et al. | 2015 | Framework analysis: a worked example of a study exploring young people's experiences of depression | Qualitative Research in Psychology | abstract | [10.1080/14780887.2015.1119228](https://doi.org/10.1080/14780887.2015.1119228) |
| 15 | Stol, Ralph & Fitzgerald | 2016 | Grounded theory in software engineering research | ICSE | abstract | [10.1145/2884781.2884833](https://doi.org/10.1145/2884781.2884833) |
| 16 | Blandford, Furniss & Makri | 2016 | Introduction: Behind the scenes (Qualitative HCI Research) | Synthesis Lectures on HCI | abstract | [10.2200/s00706ed1v01y201602hci034](https://doi.org/10.2200/s00706ed1v01y201602hci034); title-match flag, uncited |
| 17 | Lu & Liang | 2017 | Automatic Classification of Non-Functional Requirements from Augmented App User Reviews | EASE | abstract | [10.1145/3084226.3084241](https://doi.org/10.1145/3084226.3084241) |
| 18 | Taylor et al. | 2018 | Can rapid approaches to qualitative analysis deliver timely, valid findings to clinical leaders? | BMJ Open | abstract | [10.1136/bmjopen-2017-019993](https://doi.org/10.1136/bmjopen-2017-019993) |
| 19 | Braun & Clarke | 2019 | Reflecting on reflexive thematic analysis | Qualitative Research in Sport, Exercise and Health | abstract | [10.1080/2159676x.2019.1628806](https://doi.org/10.1080/2159676x.2019.1628806) |
| 20 | Braun & Clarke | 2019 | To saturate or not to saturate? Questioning data saturation as a useful concept for thematic analysis and sample-size rationales | Qualitative Research in Sport, Exercise and Health | abstract | [10.1080/2159676x.2019.1704846](https://doi.org/10.1080/2159676x.2019.1704846) |
| 21 | Gale, Wu, Erhardt et al. | 2019 | Comparison of rapid vs in-depth qualitative analytic methods from a process evaluation of academic detailing | Implementation Science | abstract | [10.1186/s13012-019-0853-y](https://doi.org/10.1186/s13012-019-0853-y) |
| 22 | McDonald, Schoenebeck & Forte | 2019 | Reliability and Inter-rater Reliability in Qualitative Research: Norms and Guidelines for CSCW and HCI Practice | Proc. ACM Hum.-Comput. Interact. (CSCW) | abstract | [10.1145/3359174](https://doi.org/10.1145/3359174) |
| 23 | Vaismoradi & Snelgrove | 2019 | Theme in Qualitative Content Analysis and Thematic Analysis | Forum: Qualitative Social Research | abstract | [10.17169/fqs-20.3.3376](https://doi.org/10.17169/fqs-20.3.3376) |
| 24 | Wang et al. | 2019 | A systematic mapping study on crowdsourced requirements engineering using user feedback | J. Software: Evolution and Process | abstract | [10.1002/smr.2199](https://doi.org/10.1002/smr.2199) |
| 25 | Braun & Clarke | 2020/2021 | Can I use TA? Should I use TA? Should I not use TA? Comparing reflexive thematic analysis and other pattern-based qualitative analytic approaches | Counselling and Psychotherapy Research | abstract | [10.1002/capr.12360](https://doi.org/10.1002/capr.12360); online 2020, issue 2021 |
| 26 | Braun & Clarke | 2020 | One size fits all? What counts as quality practice in (reflexive) thematic analysis? | Qualitative Research in Psychology | abstract | [10.1080/14780887.2020.1769238](https://doi.org/10.1080/14780887.2020.1769238) |
| 27 | O'Connor & Joffe | 2020 | Intercoder Reliability in Qualitative Research: Debates and Practical Guidelines | International Journal of Qualitative Methods | full-text | [10.1177/1609406919899220](https://doi.org/10.1177/1609406919899220) |
| 28 | Vindrola-Padros et al. | 2020 | Carrying Out Rapid Qualitative Research During a Pandemic | Qualitative Health Research | abstract | [10.1177/1049732320951526](https://doi.org/10.1177/1049732320951526) |
| 29 | Braun & Clarke | 2021 | Conceptual and design thinking for thematic analysis | Qualitative Psychology | abstract | [10.1037/qup0000196](https://doi.org/10.1037/qup0000196) |
| 30 | Goldsmith | 2021 | Using Framework Analysis in Applied Qualitative Research | The Qualitative Report | abstract | [10.46743/2160-3715/2021.5011](https://doi.org/10.46743/2160-3715/2021.5011) |
| 31 | Ramanadhan et al. | 2021 | Pragmatic approaches to analyzing qualitative data for implementation science: an introduction | Implementation Science Communications | abstract | [10.1186/s43058-021-00174-1](https://doi.org/10.1186/s43058-021-00174-1) |
| 32 | Braun & Clarke | 2022 | Toward good practice in thematic analysis: Avoiding common problems and be(com)ing a knowing researcher | International Journal of Transgender Health | abstract | [10.1080/26895269.2022.2129597](https://doi.org/10.1080/26895269.2022.2129597) |
| 33 | Proudfoot | 2022 | Inductive/Deductive Hybrid Thematic Analysis in Mixed Methods Research | Journal of Mixed Methods Research | abstract | [10.1177/15586898221126816](https://doi.org/10.1177/15586898221126816) |
| 34 | Díaz et al. | 2022 | Applying Inter-Rater Reliability and Agreement in collaborative Grounded Theory studies in software engineering | Journal of Systems and Software | abstract | [10.1016/j.jss.2022.111520](https://doi.org/10.1016/j.jss.2022.111520) |
| 35 | Dąbrowski et al. | 2022 | Analysing app reviews for software engineering: a systematic literature review | Empirical Software Engineering | abstract | [10.1007/s10664-021-10065-7](https://doi.org/10.1007/s10664-021-10065-7) |
| 36 | Saunders et al. | 2023 | Practical thematic analysis: a guide for multidisciplinary health services research teams engaging in qualitative analysis | BMJ | abstract | [10.1136/bmj-2022-074256](https://doi.org/10.1136/bmj-2022-074256) |
| 37 | Hoda | 2024 | Qualitative Research with Socio-Technical Grounded Theory | Springer (book) | abstract | [10.1007/978-3-031-60533-8](https://doi.org/10.1007/978-3-031-60533-8) |

All 37 DOIs were checked and resolve; the script reported no broken DOIs.
Session identifier: `thematic-analysis-methodology-m14vkbs4nduntnrdvajiqltnlk`.
