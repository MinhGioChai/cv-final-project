# Paired evaluation of saved predictions

Evaluation scope is engineering_pilot.

Selected rows 10. Expected inferences 20. Raw attempts 20.

| Dataset | Task | EN accuracy | VI accuracy | Jointly valid pairs | Disagreement |
|---|---|---|---|---|---|
| repope | object_existence | 100.00% | 90.00% | 10 | 10.00% |

## RePOPE jointly valid negatives

Eligible pairs 5. Image clusters 5. Excluded pairs 0.

FPR EN 0.00%. FPR VI 20.00%.

Delta FPR VI minus EN is 20.0 percentage points.

Accuracy uses all expected rows and scores invalid, failed and missing predictions as incorrect.

Image QA and translation status counts are recorded in the JSON report.

Each paired row records its selected raw source line and attempt for auditing.
