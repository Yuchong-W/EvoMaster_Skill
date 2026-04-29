# Taxonomy Case Study Draft

Date: 2026-05-01

## Why This Is The Primary Case

`taxonomy-tree-merge` is the strongest primary case because it combines all of
the ingredients the paper needs in one task:

- a clean failed-to-solved transition in the frozen suite
- real task artifacts validated by the official checks
- a visible bundled executable skill, which keeps the claim honest
- an explicit rejected post-pass candidate, which shows that the pipeline does
  not accept every optimization attempt

## Minimal Factual Record

Baseline frozen latest:

- status: `abandoned`
- duration: `300.47s`
- outcome: no passing solve record

Current frozen latest:

- status: `solved`
- final model: `gpt-5.2`
- top-level duration: `1028.40s`
- base-attempt event duration: `338.07s`
- effective total tokens on the solved event: `23410`

Current post-pass outcome:

- candidate skill: `taxonomy-tree-merge-fast`
- result: rejected
- note: `candidate failed official real test`

## Mechanism Evidence

Task-local bundled skill:

- `hierarchical-taxonomy-clustering`

Executable bundled pipeline:

- `case/tasks/taxonomy-tree-merge/environment/skills/hierarchical-taxonomy-clustering/scripts/pipeline.py`

Direct artifact validation already recorded in repo history:

- `unified_taxonomy_full.csv`: `8,968` rows
- `unified_taxonomy_hierarchy.csv`: `469` rows
- official checks passed: `22 / 22`

## Paper Narrative

The strongest reading of this case is not that `MasterSkill` invented the core
taxonomy method from scratch. The stronger and safer claim is that the pipeline
successfully leveraged an executable bundled prior, validated it in the real
task environment, preserved the passing path in the frozen current suite, and
rejected a regressive follow-up optimization.

This is important because it demonstrates benchmark-driven skill optimization as
an execution-and-validation discipline, not merely as a retrieval library and
not merely as blind prompt compression.

## Safe Claim

Safe claim for the paper:

- `MasterSkill` turns `taxonomy-tree-merge` from failed to solved in the frozen
  suite while preserving official-test discipline and rejecting a regressive
  post-pass candidate

## Unsafe Claim

Unsafe claim for the paper:

- `MasterSkill` autonomously invents the key taxonomy method from scratch

## Suggested Paragraph Skeleton

1. In the frozen baseline suite, `taxonomy-tree-merge` remained unsolved.
2. In the frozen current suite, the task is solved under `gpt-5.2`.
3. The key enabling prior is an executable bundled taxonomy pipeline, not a
   seedless method invention.
4. The important system behavior is that the pipeline can convert that prior
   into a validated benchmark solve and then reject a regressive follow-up
   candidate.
5. This makes the task the clearest end-to-end demonstration of chain value in
   the current paper.

## Figure Notes

Suggested timeline figure:

1. baseline fail
2. bundled executable prior available
3. current solved run
4. artifact validation
5. rejected fast candidate
