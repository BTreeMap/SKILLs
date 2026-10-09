# Firewall: Objections That Do Not Enter

Load with every bank. Test each objection against this list before noting
it; a match is dropped, demoted to `question`, or re-shaped into the
legitimate form named.

| Pattern | Rule |
| --- | --- |
| "Not novel" or "incremental" without a corpus key | Refused by the gate; find the prior work or drop it |
| No state-of-the-art result | Not an objection; a paper can teach without winning. Object only when the paper claims SOTA (`sota`) |
| Missing comparison to work published after the paper's date | Refused by the gate's date test |
| Missing comparison to unpublished, contemporaneous, or the reviewer's own preferred method | Drop |
| "Too simple" or "not enough math" | Drop; simplicity with evidence is a strength |
| The authors' stated limitation restated as a weakness | `minor` at most, per `limitations`; weight goes to what they did not state |
| "More experiments" without the claim the experiment would test | `question`, and the text names the claim |
| Wrong choice of task, dataset, or field for the reviewer's taste | Drop unless the claim itself names a broader scope (`overreach`) |
| Writing, grammar, figure style | Not an objection; list under points that did not affect the recommendation in `report` |
| Length, venue fit, prestige of authors or citations | Drop |
| A result the reviewer believes is wrong from memory | Pad note until a quote or a corpus key supports it |

## Re-shaping

"Not novel" becomes `prior` once the work is found; "needs more experiments"
becomes `unsupported` once the untested claim is named; "weak baseline"
becomes `baseline` once the tuning sentence is quoted or `sota` once the
stronger corpus result is keyed.
