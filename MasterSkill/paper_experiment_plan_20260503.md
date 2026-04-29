# Paper Experiment Plan for Stronger Evidence

Date: 2026-05-03

## Purpose

This document lists the highest-value additional experiments for improving the
paper's competitiveness and credibility without reopening the scope into an
unfocused benchmark expansion.

The governing principle is:

- add experiments only when they strengthen a specific paper claim
- prefer experiments that sharpen attribution and stability over experiments
  that merely add more raw logs

## Current Claim Baseline

The paper already supports:

- suite-level coverage gain on a frozen `15`-task slice:
  - baseline solved: `3 / 15`
  - current solved: `6 / 15`
- one strong primary case:
  - `taxonomy-tree-merge`
- several useful supporting optimization traces:
  - `financial-modeling-qa`
  - `enterprise-information-search`
  - `pddl-tpp-planning`

The paper does **not** yet strongly support:

- stability across repeated runs
- clean attribution of which chain components are necessary
- a broader efficiency story beyond selected tasks

## Priority Order

1. primary-case attribution experiments
2. stability reruns on main claims
3. selected chain ablations
4. trace-level optimization evidence packaging

## Experiment Group A: Primary-Case Attribution

### A1. Taxonomy Bundled-Prior Dependence

Question:

- is the `taxonomy-tree-merge` gain critically dependent on bundled-prior reuse?

Minimal design:

- run the current pipeline on `taxonomy-tree-merge` with bundled-prior access enabled
- run a controlled variant with bundled-prior access disabled or bypassed at the
  case level

Desired outcome:

- quantify whether the solve depends on the bundled prior
- convert the current qualitative caution into direct evidence

Paper value:

- this experiment makes the main case more honest and more convincing
- it turns “we should not overclaim autonomous invention” into a measured result

Risk:

- if disabling prior access still solves, that is still useful because it raises
  the autonomy claim ceiling
- if it fails, that cleanly supports the bundled-prior interpretation

### A2. Taxonomy Post-Solve Rejection Sanity Check

Question:

- is the rejected `taxonomy-tree-merge-fast` candidate reproducibly regressive?

Minimal design:

- rerun the candidate verification path once or twice
- confirm that the rejection is not a one-off logging artifact

Desired outcome:

- stable confirmation that the post-solve candidate fails official evaluation

Paper value:

- strengthens the “validation-and-rejection” narrative in the strongest case

## Experiment Group B: Stability Reruns

### B1. Primary-Case Repeat Runs

Tasks:

- `taxonomy-tree-merge`
- `xlsx-recover-data`

Question:

- are the solve-gain cases stable under a small number of reruns?

Minimal design:

- rerun each task `2` additional times under the same paper-facing configuration
- record solved/failed status and major trace differences

Desired outcome:

- show that the main solve-gain claims are not single-run accidents

Paper value:

- one small stability table can substantially improve reviewer trust

### B2. Supporting-Case Repeat Runs

Tasks:

- `financial-modeling-qa`
- `enterprise-information-search`

Question:

- are the post-solve rejection patterns stable?

Minimal design:

- rerun each task `1` or `2` additional times
- record whether:
  - base solve remains stable
  - follow-up candidate remains rejected

Desired outcome:

- show that the system’s post-solve behavior is repeatable

Paper value:

- turns the supporting traces from anecdotes into low-cost stability evidence

## Experiment Group C: Chain Ablations

### C1. No Post-Solve Optimization

Question:

- how much paper value depends on post-solve optimization versus the solve path itself?

Minimal design:

- run a selected subset with post-solve optimization disabled:
  - `taxonomy-tree-merge`
  - `financial-modeling-qa`
  - `enterprise-information-search`

Desired outcome:

- show whether the current narrative actually needs the post-solve stage

Paper value:

- if the solve remains but rejection evidence disappears, that cleanly separates
  solve coverage from refinement behavior

### C2. No Candidate Refinement / No Research Variant

Question:

- does the chain still solve or optimize key tasks if refinement is removed?

Minimal design:

- implement a controlled reduced pipeline mode for a very small subset
- recommended first target:
  - `taxonomy-tree-merge`

Desired outcome:

- identify whether the gain is mostly:
  - base attempt
  - bundled prior
  - refinement / validation loop

Paper value:

- high attribution value, but more implementation risk than the other experiments

## Experiment Group D: Trace-Level Optimization Evidence

### D1. Financial Modeling QA Efficiency Table

Question:

- can we present `financial-modeling-qa` as a clean compact optimization case?

Minimal design:

- package baseline/current comparison and repeated current traces into one small table
- fields:
  - status
  - top-level duration
  - effective total tokens
  - whether follow-up candidate was rejected

Paper value:

- creates the cleanest main-text supporting case

### D2. PDDL Event-Level Optimization Table

Question:

- can `pddl-tpp-planning` be defended as a trace-level optimization example
  despite weak top-level runtime comparison?

Minimal design:

- extract:
  - base-attempt duration
  - accepted optimized event duration
  - base event tokens
  - optimized event tokens

Paper value:

- useful appendix table
- shows that event-level gains can exist even when top-level suite duration is mixed

## Recommended Execution Plan

### Must-Do

1. `A1` Taxonomy bundled-prior dependence
2. `B1` Repeat runs for `taxonomy-tree-merge` and `xlsx-recover-data`
3. `B2` Repeat runs for `financial-modeling-qa` and `enterprise-information-search`

Reason:

- these are the best tradeoff between cost and paper strength

### Should-Do

4. `A2` Taxonomy post-solve rejection sanity check
5. `D1` Financial modeling compact evidence table
6. `D2` PDDL event-level optimization table

Reason:

- these do not greatly expand scope, but noticeably improve the paper’s analysis layer

### Optional / Higher Risk

7. `C1` No post-solve optimization ablation
8. `C2` Reduced-chain ablation

Reason:

- these could be high value, but they require more implementation control and may
  cost more time than the immediate return justifies

## What To Avoid

- do not restart a new broad full-suite sweep unless the paper-facing suite is invalidated
- do not add many new tasks just to increase table size
- do not run expensive ablations on weak tasks first
- do not spend time polishing prose before the high-value evidence above is addressed

## Deliverables If These Experiments Succeed

- one small stability table
- one primary-case attribution paragraph backed by direct evidence
- one supporting-case efficiency table
- one appendix optimization trace table
- stronger and narrower method claims that are harder to challenge
