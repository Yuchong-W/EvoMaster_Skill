# MasterSkill Paper Outline Draft

Date: 2026-05-01

## Working Title

Benchmark-Driven External Skill Optimization for Realistic SkillsBench Tasks

## One-Sentence Claim

`MasterSkill` is a benchmark-driven external-skill optimization pipeline that
improves frozen-suite solve coverage on `SkillsBench` and exposes a concrete,
traceable optimization chain on hard real-environment tasks.

## Section Plan

### 1. Introduction

Target message:

- many task environments are too brittle or too expensive for naive one-shot execution
- external skills are useful, but static skill libraries do not explain how to discover, validate, refine, or reject them
- benchmark-driven optimization is the key idea: use official-task feedback to drive chain-level improvement

Evidence sources:

- full-suite frozen compare
- `taxonomy-tree-merge` failed-to-solved case
- supporting optimization traces from common-solved tasks

Do not overclaim:

- do not present this as broad proof of universal efficiency gains
- do not imply weight updates or model fine-tuning

### 2. Problem Setting

Target message:

- fixed base model
- external skill interface
- real task environments
- official test as the only success criterion

Evidence sources:

- runtime configuration and latest-suite setup
- baseline/current roots under `MasterSkill/masterskill_data_phase1_*`

Do not overclaim:

- do not collapse bundled task-local priors into autonomous invention claims
- do not imply that historical exploratory roots are part of the frozen paper suite

### 3. Method: MasterSkill

Target message:

- `MasterSkill` is a loop for attempting, analyzing, reusing, generating,
  validating, and refining external skills under benchmark feedback

Subsections to write:

- base attempt
- task analysis
- skill reuse and bundled prior access
- candidate generation / refinement
- official-test validation
- post-pass optimization
- rejection of regressive candidates

Evidence sources:

- runtime control-flow description already captured in `state.md`
- case-study traces from `taxonomy-tree-merge`, `financial-modeling-qa`, and
  `pddl-tpp-planning`

Do not overclaim:

- do not say every improvement comes from autonomous skill creation
- do not say post-pass always improves the original solve

Figure:

- one system diagram for the full loop

### 4. Experimental Setup

Target message:

- the evaluation is a frozen, real-environment comparison under a fixed model
  policy

Need to state explicitly:

- `SkillsBench` frozen task set
- baseline root and current root
- official tests
- execution constraints
- model policy

Evidence sources:

- `paper_results_table_20260430.md`
- `paper_tasks_20260430.md`
- the rerun-normalized `latest` roots

Do not overclaim:

- do not imply that historical archival runs are part of the reported suite

### 5. Main Results

Target message:

- the suite-level evidence supports coverage gain with no solve losses

Main table source:

- use `data/papers/paper_results_table_20260430.md` as source material

Main points to write:

- baseline solved `3 / 15`
- current solved `6 / 15`
- solve gains: `seismic-phase-picking`, `taxonomy-tree-merge`, `xlsx-recover-data`
- no solve losses
- common-solved tasks do not support a broad runtime-win claim

Evidence sources:

- `paper_results_table_20260430.md`
- latest benchmark JSON files in baseline/current roots

Do not overclaim:

- do not frame `seismic-phase-picking` as the main mechanism case
- do not convert common-solved trace improvements into a broad suite efficiency claim

### 6. Case Study: Taxonomy Tree Merge

Target message:

- this is the clearest end-to-end demonstration of chain value in the current
  paper

Why this case:

- strongest failed-to-solved comparison
- direct artifact confirmation
- post-pass candidate rejection also visible

Need to include:

- baseline failure
- current success
- executable bundled pipeline evidence
- what part is likely:
  - bundled-skill leverage
  - orchestration / validation improvement
  - post-pass rejection logic

Evidence sources:

- `taxonomy_case_study_sources_20260430.md`
- `taxonomy_case_study_draft_20260501.md`
- latest baseline/current taxonomy JSON files

Do not overclaim:

- do not say the core taxonomy method was invented from scratch
- do not say the post-pass candidate improved the winning path

Figure:

- one timeline or evidence-flow figure for `taxonomy-tree-merge`

### 7. Supporting Cases

Target message:

- the optimization chain has meaningful behavior beyond the primary case, but
  the evidence is heterogeneous

Candidate tasks:

- `enterprise-information-search`
- `financial-modeling-qa`
- `pddl-tpp-planning` (optional appendix optimization example)

Purpose:

- show accepted optimization / refinement behavior
- not to overclaim broad suite efficiency

Evidence sources:

- `supporting_cases_20260501.md`
- latest current JSON traces for the three tasks

Do not overclaim:

- do not present `enterprise-information-search` as a runtime win
- do not present `pddl-tpp-planning` top-level duration as improved

### 8. Limitations

Target message:

- the paper is credible because it states exactly where the evidence stops

Must state:

- suite is small and claim is narrow
- many failures remain `abandoned_without_classification`
- frozen current root currently supports coverage-gain claims better than broad efficiency claims
- historical exploratory runs used other models, but the paper-facing frozen
  comparison uses `gpt-5.2`

Evidence sources:

- frozen results table
- attribution draft
- rerun-normalized latest roots

Do not overclaim:

- do not blur paper-facing results with exploratory development logs

### 9. Conclusion

Target message:

- benchmark-driven external skill optimization is promising even before it is
  universal

Conclude with:

- benchmark-driven external skill optimization is promising
- the strongest current evidence is coverage expansion plus explicit chain-level artifacts
- broader efficiency and transfer claims remain future work

## Figures To Prepare

1. System loop diagram
   Caption goal: show the attempt -> analyze -> reuse/generate -> official-test
   validation -> post-pass refine/reject cycle.
2. Taxonomy case-study timeline
   Caption goal: show failed baseline, bundled executable prior, solved current
   run, artifact validation, and rejected fast candidate.
3. Optional small attribution chart for selected tasks
   Caption goal: distinguish coverage-gain cases from optimization-only cases.

## Tables To Prepare

1. Main suite comparison table
   Source: `paper_results_table_20260430.md`
2. Selected task attribution table
   Source: `paper_attribution_table_20260430.md`
3. Optional case-study trace table for `taxonomy-tree-merge`
   Source: `taxonomy_case_study_draft_20260501.md`

## Open Decision

Before this outline is turned into a paper draft, decide:

- whether to keep `pddl-tpp-planning` as a main supporting optimization case or
  move it to appendix
- whether `xlsx-recover-data` deserves a short mechanism subsection or only a
  brief solve-gain mention
