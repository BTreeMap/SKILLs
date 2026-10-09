# Literature review: what are the main methodological approaches to thematic analysis, and how do they differ in procedure, epistemological commitments, and quality criteria?

## Summary

Included literature describes a family of pattern-finding procedures that
share vocabulary and disagree about what a code is, what a theme is, and
whether coding can be correct. Four positions recur: approach organised
around coding accuracy and multiple coders; approach organised around shared
codebook applied by team; approach treating analyst's interpretation as
instrument and rejecting accuracy as standard; set of matrix-based
procedures trading interpretive depth for auditability across many cases.
These positions carry incompatible quality criteria, so procedure borrowed
from one and justification borrowed from another produces work satisfying
neither. Sharpest live disagreement: whether agreement between coders
evidences anything; corpus contains both worked procedure for measuring it
and argument that measuring it misdescribes what qualitative analysis does.
For data this review targets (user feedback, bug tickets, other high-volume
operational text), computing literature in corpus has largely pursued
automated classification into fixed categories, leaving theme development
aside; the two literatures address different problems; no study in corpus
reconciles them.

## Method

Searches ran on 2026-08-28 against OpenAlex (31 queries), Crossref (7
queries), and six OpenAlex snowball cycles (backward and forward) seeded
from Braun & Clarke 2006 [6], McDonald et al. 2019 [22], and Gale et al.
2013 [11]. That date is review's as-of point. Session script logged every
query; every search returned result set truncated against upstream totals in
the thousands to millions, so corpus is relevance-ranked sample, not
enumeration of field.

Criteria fixed before first search. Inclusion required methodological
contribution to thematic analysis: proposing, codifying, critiquing, or
comparing named approach, its procedure, or its quality criteria. One change
recorded mid-review, after requester specified target application is user
feedback and HCI-style qualitative data, not psychology-default methodology.
Change added inclusion criterion for methodologically reflective work on
user feedback, tickets, app reviews, and HCI, CSCW, or software-engineering
qualitative data, and triggered further find cycle and full re-screen under
changed criteria.

| Flow | N |
| --- | --- |
| Records identified and deduplicated into the corpus | 574 |
| Excluded at title/abstract screening | 537 |
| Included | 37 |
| Included at full-text read level | 3 |
| Included at abstract read level | 34 |

Largest exclusion categories: general qualitative-methods material with no
distinct contribution to thematic analysis (190); substantive empirical
studies with no methodological commentary (67 plus 27 applications of
thematic analysis and 24 domain studies); term collisions where "analysis",
"taxonomy", or "classification" matched natural-science and algorithmic work
(38). Seven of 37 included papers entered through snowball cycles, not
keyword search, concentrated in intercoder reliability and rapid-analysis
strands.

## Thematic analysis names a family of methods

Corpus's organising claim: approaches sharing the name differ enough to be
separate methods. Braun & Clarke [25] set out typology of pattern-based
approaches separating coding reliability, codebook, reflexive, and thematic
coding variants, cut across distinction between small-q work operating
inside (post)positivist frame and big-Q work that does not. Their stated aim
in that paper: informed selection among methods.

Corpus supports descriptive claim that schools coexist, from independent
author groups. Boyatzis [3] presents thematic analysis as way of moving
between qualitative and quantitative traditions, codes developed
systematically and checked for reliability. Guest et al. [8] present applied
variant built on codebooks and structured team coding. Aronson [2], writing
before any of these, describes deliberately loose procedure of collecting
data, identifying patterns, combining them into themes: evidence the name
covered informal practice before it was codified. Braun & Clarke [6] then
codified six-phase version rest of corpus positions itself against.

Stronger claim, that schools are mutually incompatible, comes predominantly
from one author group. Braun & Clarke argue it across four included papers
[19][25][26][32]; their argument that generic quality checklists misjudge
reflexive thematic analysis [26] is untested position statement. Independent
support in corpus is indirect, from one paper: Stol et al. [15] diagnose
same failure mode in software engineering, where method is named in paper
without its procedure being followed. They reach that conclusion about
grounded theory, so it corroborates pattern while specific claim about
thematic analysis stays uncorroborated.

This section rests on abstract-level reading of [6] and [25]; see
Limitations.

## Where the schools differ: the code, the theme, and who decides

Corpus locates disagreement in three places.

What a code is. In coding-reliability and codebook lineages, code is label
whose application can be right or wrong: what makes agreement measurable.
O'Connor & Joffe [27], read at full text, build eight-step procedure on that
premise and recommend maximum of 30 to 40 codes, preferably 20 or fewer. In
reflexive account, code is analytic product of researcher's engagement, so
accuracy is not defined for it [19][25].

What a theme is. Attride-Stirling [4] treats themes as tiers to be
constructed and displayed: Basic themes cluster into Organizing themes,
which resolve into Global theme, with practical guidance of roughly 5 to 14
groupings per network and caution that networks are a tool within analysis,
never its whole. Braun & Clarke [32] distinguish themes as shared patterns
of meaning from topic summaries merely grouping everything said about a
subject, treating latter as common failure. Vaismoradi et al. [10] and
Vaismoradi & Snelgrove [23] locate related boundary between thematic
analysis and qualitative content analysis, turning on whether counting codes
is admissible and on what "theme" denotes.

Whether prior structure is allowed. Fereday & Muir-Cochrane [5], read at
full text, run hybrid in six stages: develop code manual from theory, test
its reliability with second coder, summarise data, apply template while
letting data-driven codes emerge, cluster codes into themes, corroborate
those themes against original data. Their own case shows mechanism: code for
"trust and respect" began nested inside theory-derived category and was
promoted to separate data-driven code. Template analysis [9][12] formalises
same move differently: initial template, often carrying a priori themes,
built on data subset, then revised iteratively against whole. Proudfoot [33]
sequences inductive and deductive passes within mixed methods designs. These
procedures are incompatible with reflexive position that themes are
constructed by analyst, never found against prior frame; corpus contains no
study testing which produces better analyses.

## Multiple coders and reliability: the corpus's sharpest disagreement

Both sides represented by independent author groups; corpus does not resolve
disagreement.

O'Connor & Joffe [27] give affirmative case its operational form: decide
coder count, data proportion, coding unit, code depth, statistic, and
threshold in advance; build frame through immersion; second coder works
independently prepared subset; compute per-code reliability; discuss and
refine; then apply final frame. They recommend double-coding 10 to 25% of
data units and report conventional interpretive bands, values above 0.9
acceptable to all and above 0.8 acceptable to many, citing Landis & Koch
scale. They also name where it does not belong: recursive designs such as
grounded theory, purely exploratory work, analyses prioritising depth over
consistency. Their own framing limits the claim: "ICR is never an end in
itself; it is merely a means to the ultimate goal of achieving an insightful
and robust qualitative analysis." MacPhail et al. [13] supply second,
independent set of process guidelines; Artstein & Poesio [7] supply
statistical treatment of agreement coefficients from computational
linguistics.

Braun & Clarke [19][25][26] hold opposing position: agreement between coders
cannot evidence quality where coding is interpretive, so reporting it
alongside reflexive procedure misdescribes what was done.

McDonald et al. [22] is corpus's empirical contribution to this disagreement
and the one paper addressed directly to computing practice. Their
meta-analysis of CSCW and HCI papers from 2016 to 2018 reports inter-rater
reliability appears in roughly one in nine qualitative papers; they argue
field needs epistemology-specific reporting norms, no blanket rule. Read at
abstract level here; one-in-nine figure comes from its abstract and indexed
summaries. Díaz et al. [34] apply agreement measures within collaborative
software-engineering studies, showing practice has applied-computing
constituency independent of health and psychology literatures.

## Matrix and template procedures for team and high-volume settings

Distinct group of included papers trades interpretive depth for auditability
across cases: property that matters when many records must be handled by
more than one person.

Gale et al. [11], read at full text, set out Framework Method in seven
stages: transcription, familiarisation, coding, developing working
analytical framework, applying that framework, charting into matrix whose
rows are cases and columns are codes, interpretation. Matrix is mechanism:
reduces volume while keeping each case's context, retains quotation
references for illustration. They recommend at least two researchers, or one
from each discipline in multidisciplinary team, independently code first few
transcripts where feasible. They also state method's boundary condition:
"The Framework Method cannot accommodate highly heterogeneous data, i.e.
data must cover similar topics or key issues so that it is possible to
categorize it." Two further included papers [14][30] describe same method in
applied use. Miles & Huberman [1] are corpus's earlier statement of
underlying idea: data reduction and data display are analytic operations.

Rapid-analysis strand pushes further in same direction, replacing
line-by-line coding with templated summaries and matrix displays to reach
decision-makers on compressed timelines [18][21][28][31]. Saunders et al.
[36] make team-facing case explicitly, arguing practical guidance for
non-specialists is sparse and non-specialist perspectives can enrich
interpretation. Taylor et al. [18] and Gale et al. [21] each compare rapid
against fuller analysis in single applied setting, which does not establish
equivalence in general (see Gaps); all four rapid-analysis papers read at
abstract level here.

## Analysis of user feedback in computing has developed separately

Included computing papers on user feedback do something different from
thematic analysis literature. Dąbrowski et al. [35] survey app-review
analysis for software engineering, Wang et al. [24] map crowdsourced
requirements engineering built on user feedback, Lu & Liang [17] classify
non-functional requirements from app reviews. Work in this strand is
oriented toward assigning high volumes of feedback to predefined categories
such as bug report, feature request, or requirement type. Theme development,
in the sense thematic analysis literature uses, is not the objective. Both
[35] and [24] are surveys, so what they say of individual primary studies is
reported here as their account.

The two literatures in this corpus meet only at McDonald et al. [22] and
software-engineering reliability and grounded-theory work [15][34][37], all
concerning researchers' qualitative practice, none reading of product
feedback.

## Mapping onto a thematic analysis skill

Design guidance derived from synthesis, beyond what literature finds.

Corpus's central implication for a skill: "do a thematic analysis" is
underspecified. Skill emitting one procedure produces work whose method and
justification come from different schools: failure Braun & Clarke [32] and,
for different method, Stol et al. [15] both describe. First move should be
selecting approach; selection should be recorded.

| Approach | Corpus records | Fits when | Quality standard it answers to |
| --- | --- | --- | --- |
| Reflexive | [6][19][25][26][29][32] | Open question, one analyst or genuinely collaborative pair, meaning matters more than counts | Reflexivity and coherence of interpretation; agreement statistics rejected |
| Codebook / coding reliability | [3][7][8][13][22][27][34] | Several people must code consistently; results feed decision | Documented codebook, declared agreement procedure and threshold |
| Template | [9][12] | Working taxonomy exists and should evolve | Template versioning and revision history |
| Framework / matrix | [1][11][14][30] | Many cases, comparison across them, mixed-expertise team | Auditable matrix; requires reasonably homogeneous data [11] |
| Rapid / templated summary | [18][21][28][31][36] | Deadline-bound triage feeding decision | Explicit statement of what depth was traded away |
| Hybrid inductive/deductive | [5][33] | Prior categories exist but must not foreclose new ones | Both passes documented; promotion of codes traceable [5] |

Concrete defaults corpus supplies, so skill invents none: double-code 10 to
25% of units when running agreement check, keep codebook to at most 40
codes, aiming for 20 or fewer, fix coder count, unit, statistic, threshold
before coding starts, all from O'Connor & Joffe [27]; aim for roughly 5 to
14 theme groupings, from Attride-Stirling [4]; at least two people
independently code first few records in multidisciplinary team, from Gale et
al. [11]. Each is one source's recommendation; [27] and [11] read at full
text, [4] not.

Behaviours corpus warrants skill guarding against: reporting agreement
statistics alongside reflexive procedure [19][25][26]; producing topic
summaries and calling them themes [32]; invoking saturation as sample-size
rationale for interpretive work, which Braun & Clarke [20] argue is
incoherent because meaning is generated in analysis; pushing heterogeneous
material through matrix method whose stated precondition is topical
similarity [11].

For feedback and ticket data specifically, corpus offers no validated
procedure, so skill should present that as its own adaptation. Framework and
rapid strands are closest structural fit, since tickets are many, short,
comparable across cases; computing strand [17][24][35] indicates volume
problem is usually solved by classification into fixed categories, a
different operation with different failure modes.

## Limitations of this review

Read level is main limitation. Only 3 of 37 included papers read at full
text: Fereday & Muir-Cochrane [5], Gale et al. [11], O'Connor & Joffe [27].
Publisher access controls blocked full text for the rest, including every
Braun & Clarke paper, corpus's most-cited author group and source of its
organising typology. Procedural detail for Braun & Clarke [6][25] and
Attride-Stirling [4] obtained from publisher records and secondary
methodological summaries. Weaker than reading primary text; check those step
lists against originals before hard-coding them into a skill.

Beyond truncation noted under Method, Nowell et al.'s 2017 paper on
trustworthiness criteria for thematic analysis, frequently cited in this
area, was not retrieved by any query, so it is absent from corpus and
uncited here. Books indexed unevenly: Boyatzis [3] carries no DOI and
entered under title key; Miles & Huberman [1] carries journal venue in its
record that is indexing artefact.

One verification flag not cleared. Record at [16] resolves through DOI
redirect to Springer reissue; its Crossref title match is 0.33 because
corpus holds chapter title against book-level record. I could not reach
landing page to confirm item, found no retraction indication, and therefore
kept it in bibliography without citing it for any claim.

Screening used pattern rules applied to titles and keys with recorded reason
for each of 537 exclusions, not reading every abstract. Faster and less
accurate than abstract-level screening; will have excluded some eligible
papers whose titles did not signal methodological contribution. One such
case visible in state file: critical review of how reflexive thematic
analysis is reported in Health Promotion International
(doi:10.1093/heapro/daae049) excluded by default rule although it plausibly
satisfies inclusion criterion. Named here without citation because it is in
excluded set. Re-screen at abstract level would likely recover it and others
like it, strengthening independent evidence for section on whether schools
are incompatible.

## Gaps and open questions

None of 37 included papers applies or evaluates thematic analysis procedure
on bug tickets, issue-tracker data, or support transcripts.

None compares interpretive theme development against automated category
classification on same body of user feedback, so corpus cannot say what
classification-oriented computing work [17][24][35] gives up.

Reliability disagreement rests on position statements on one side
[19][25][26] and procedural guidance on the other [13][27], with one
descriptive meta-analysis of reporting practice [22]. No included paper
tests whether measuring agreement changes quality of resulting analysis.

Rapid and templated analysis compared against fuller analysis in two
single-setting studies [18][21]. Whether reduction is safe in general, and
for which decisions, not established by this corpus.

Claims that schools are mutually incompatible come predominantly from one
author group across four included papers [19][25][26][32]; independent
corroboration in corpus is indirect [15].

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
Session identifier:
`thematic-analysis-methodology-m14vkbs4nduntnrdvajiqltnlk`.
