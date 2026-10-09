# Firewall: Objections That Do Not Enter

Load with every bank. Test each objection against this list before noting
it; match is dropped, demoted to `question`, or re-shaped into legitimate
form named.

| Pattern | Rule |
| --- | --- |
| "Not novel" or "incremental" without corpus key | Refused by gate; find prior work or drop it |
| No state-of-the-art result | Not objection; paper can teach without winning. Object only when paper claims SOTA (`sota`) |
| Missing comparison to work published after paper's date | Refused by gate's date test |
| Missing comparison to unpublished, contemporaneous, or reviewer's own preferred method | Drop |
| "Too simple" or "not enough math" | Drop; simplicity with evidence is strength |
| Authors' stated limitation restated as weakness | `minor` at most, per `limitations`; weight goes to what they did not state |
| "More experiments" without claim experiment would test | `question`; text names claim |
| Wrong choice of task, dataset, or field for reviewer's taste | Drop unless claim itself names broader scope (`overreach`) |
| Writing, grammar, figure style | Not objection; list under points that did not affect recommendation in `report` |
| Length, venue fit, prestige of authors or citations | Drop |
| Result reviewer believes wrong from memory | Pad note until quote or corpus key supports it |

## Re-shaping

"Not novel" becomes `prior` once work is found; "needs more experiments"
becomes `unsupported` once untested claim is named; "weak baseline" becomes
`baseline` once tuning sentence is quoted, or `sota` once stronger corpus
result is keyed.
