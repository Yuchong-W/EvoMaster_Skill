# Taxonomy Case Study Source Map

Date: 2026-04-30

## Purpose

This file maps the primary `taxonomy-tree-merge` case study claim to concrete
artifacts already in the repository.

## Task Definition

Primary task instruction:

- [instruction.md](/home/yuchong/auto-research-team/MasterSkill/case/tasks/taxonomy-tree-merge/instruction.md)

Task goal:

- unify three e-commerce taxonomies into a shared 5-level category system
- write:
  - `unified_taxonomy_full.csv`
  - `unified_taxonomy_hierarchy.csv`

## Baseline Failure Evidence

Frozen pre-evolution baseline:

- [taxonomy-tree-merge.json](/home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_pre_evolution/benchmark_runs/latest/taxonomy-tree-merge.json)

Legacy pure baseline comparison file:

- [taxonomy-tree-merge.json](/home/yuchong/auto-research-team/MasterSkill/masterskill_data_pre_evolution/benchmark_runs/latest/taxonomy-tree-merge.json)

Current summary of the baseline side:

- status: `abandoned`
- failure mode: timeout / abandoned baseline path
- interpretation:
  - pure base attempt does not solve the task cleanly under the baseline setup

## Current Success Evidence

Frozen current file:

- [taxonomy-tree-merge.json](/home/yuchong/auto-research-team/MasterSkill/masterskill_data_phase1_current/benchmark_runs/latest/taxonomy-tree-merge.json)

Legacy current comparison file:

- [taxonomy-tree-merge.json](/home/yuchong/auto-research-team/MasterSkill/masterskill_data/benchmark_runs/latest/taxonomy-tree-merge.json)

Current summary of the current side:

- status: `solved`
- final model: `gpt-5.2`
- top-level duration: `1028.40s`
- event-level base-solve duration: `338.07s`
- event-level effective tokens: `23410`

## Bundled Skill And Pipeline Evidence

Bundled task-local skill:

- [SKILL.md](/home/yuchong/auto-research-team/MasterSkill/case/tasks/taxonomy-tree-merge/environment/skills/hierarchical-taxonomy-clustering/SKILL.md)

Executable pipeline:

- [pipeline.py](/home/yuchong/auto-research-team/MasterSkill/case/tasks/taxonomy-tree-merge/environment/skills/hierarchical-taxonomy-clustering/scripts/pipeline.py)

Why this matters:

- this case should not be misrepresented as seedless autonomous skill invention
- the strongest claim is that the benchmark-driven chain can successfully leverage,
  validate, and preserve a strong bundled pipeline, then reject regressive follow-up candidates

## Direct Artifact Validation Evidence

Development-log source:

- [development_log.md](/home/yuchong/auto-research-team/MasterSkill/development_log.md)

Relevant logged facts:

- direct task-image validation passed
- `unified_taxonomy_full.csv`: `8,968` rows
- `unified_taxonomy_hierarchy.csv`: `469` rows
- official checks passed: `22 / 22`

Interpretation:

- the method itself became viable inside the real task image
- later failures were increasingly about host-side completion / persistence rather than task infeasibility

## Candidate Rejection Evidence

Current latest file records a rejected post-pass candidate:

- `taxonomy-tree-merge-fast`
- note: `candidate failed official real test`

Why this matters:

- the case study can show not only a successful path
- it can also show that the system rejects a regressive optimization candidate instead of accepting every compression attempt

## Proposed Case-Study Narrative

1. baseline pure attempt fails
2. bundled executable taxonomy pipeline exists and is validated directly
3. current chain successfully converts that path into a solved benchmark record
4. a post-pass candidate is attempted
5. the regressive candidate is rejected by official-test evaluation

## Claim Boundary For This Case

Safe claim:

- `MasterSkill` can turn a hard task from failed to solved in the frozen suite while preserving official-test discipline and rejecting a regressive follow-up candidate

Unsafe claim:

- `MasterSkill` autonomously invented the key taxonomy method from scratch
