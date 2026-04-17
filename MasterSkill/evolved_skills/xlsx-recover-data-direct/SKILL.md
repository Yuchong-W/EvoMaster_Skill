# XLSX Recover Data Direct Solver

Use this skill for `xlsx-recover-data` when the task asks for a repaired
`nasa_budget_recovered.xlsx` built from `nasa_budget_incomplete.xlsx`.

## When to Use

- The workbook already contains all non-missing source values.
- Missing cells are marked with `???`.
- The verifier checks the recovered workbook contents, not an explanation.

## How to Use

1. Load `nasa_budget_incomplete.xlsx` with `openpyxl`.
2. Recover the missing cells in dependency order:
   - row totals and direct cross-sheet copies first
   - then YoY- and share-derived values
   - then downstream chain values
3. Save the result as `nasa_budget_recovered.xlsx`.
4. Validate before finishing:
   - no `???` placeholders remain
   - row totals match
   - cross-sheet values are consistent

## Suggested Command

```bash
bash /root/.skills/xlsx-recover-data-direct/scripts/run_recovery.sh
```

If the environment mirrors skills under `/root/.codex/skills`, the same script is
available there as well.
