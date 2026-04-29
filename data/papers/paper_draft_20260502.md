# Benchmark-Driven External Skill Optimization for Realistic SkillsBench Tasks

Date: 2026-05-02

## Abstract

We present `MasterSkill`, a benchmark-driven external-skill optimization
pipeline for realistic `SkillsBench` tasks. Rather than updating model weights,
`MasterSkill` keeps a fixed base model and treats skills as external artifacts
that can be reused, refined, validated, or rejected under official-task
validation. The central idea is to use benchmark execution not only as
evaluation, but also as the control signal that determines which candidate
skill paths are preserved.

We evaluate the system on a frozen `15`-task `SkillsBench` slice using a
paper-facing baseline root and a paper-facing current root, both normalized to
`gpt-5.2` for solved snapshots. On this slice, the baseline solves `3 / 15`
tasks and the current pipeline solves `6 / 15`, yielding three solve gains and
no solve losses. These results support a suite-level coverage-gain claim, but
do not support a broad claim of universal runtime improvement across
common-solved tasks.

To explain the suite-level gains, we analyze trace-level behavior on selected
tasks. The clearest case is `taxonomy-tree-merge`, which moves from failed to
solved while exposing a bundled-prior path that survives official-task
validation and a regressive follow-up candidate that is explicitly rejected.
Supporting cases including `financial-modeling-qa`,
`enterprise-information-search`, and `pddl-tpp-planning` show that the
pipeline can also evaluate post-solve refinements and reject candidates that
fail validation or degrade the solve path.

The contribution of this paper is therefore a concrete benchmark-driven loop for
external skill optimization that produces limited but real solve-coverage gains,
preserves official-task discipline, and exposes interpretable validation and
rejection behavior on hard real-environment tasks.

## 1. Introduction

Modern benchmark tasks increasingly require interaction with brittle tools,
large files, task-specific environments, and official evaluators that expose
failure modes far beyond simple one-shot question answering. In these settings,
a strong base model may still fail because the missing ingredient is not only
reasoning ability, but also access to reusable external procedures and a
reliable way to validate them against the real task environment.

External skills are a natural response to this gap. However, a static skill
library alone does not explain how a system should decide when to reuse an
existing procedure, when to refine it, when to reject it, or how to compare
candidate skills under benchmark feedback. In practice, this missing control
loop matters: many candidate procedures are partially useful, some only work
under narrow execution conditions, and some regress once they are tested in the
official environment.

This paper studies `MasterSkill`, a benchmark-driven external-skill
optimization pipeline for realistic `SkillsBench` tasks. Rather than modifying
model weights, `MasterSkill` keeps the base model fixed and treats skills as
external artifacts that can be reused, refined, validated, or rejected. The
central idea is to use official-task feedback as the optimizer: benchmark
execution is not merely a final scorecard, but the mechanism that determines
which candidate skill paths survive.

Our current evidence is intentionally narrow. On a frozen `SkillsBench` slice,
the paper-facing baseline solves `3 / 15` tasks, while the paper-facing current
pipeline solves `6 / 15`, yielding three solve gains and no solve losses. This
supports a suite-level coverage-gain claim. At the same time, the common-solved
tasks do not support a broad claim of universal runtime improvement, so the
paper does not make one.

To explain why the suite-level difference is meaningful, we pair the frozen
comparison with trace-level case analysis. The clearest case is
`taxonomy-tree-merge`, which moves from failed to solved while exposing a
bundled-prior path that survives official-task validation and a regressive
candidate that is later rejected. Supporting tasks such as
`financial-modeling-qa`, `enterprise-information-search`, and
`pddl-tpp-planning` further show that the pipeline does not merely solve tasks
once; it also evaluates post-solve refinements and rejects candidates that fail
validation or degrade the effective solve path.

The contribution is therefore not a claim that external-skill optimization is
already solved, nor a claim that every improvement comes from autonomous skill
invention. It is a concrete benchmark-driven loop that produces limited but real
solve-coverage gains, preserves official-task discipline, and exposes
interpretable chain behavior on hard real-environment tasks.

## 2. Problem Setting

We study a fixed-model setting in which the core language model is not updated
through fine-tuning or weight modification. Instead, the system may access
external skills: textual and executable artifacts that provide reusable
procedures, tools, or instructions for solving benchmark tasks. A skill may be
bundled with a task, discovered from prior work, or produced as a derived
candidate during the optimization loop.

Tasks come from a frozen `SkillsBench` slice and are executed in their real task
environments. Each task is evaluated by its official checker or official output
requirement. A run therefore succeeds only when it produces the required
artifacts in the expected environment and passes the task’s evaluation logic.
This design is important because many failures that appear minor in text-only
evaluation become decisive under real execution, including environment mismatch,
output-format drift, partial artifact generation, and regressions introduced by
over-aggressive optimization.

We compare two paper-facing roots. The first is a pre-evolution baseline that
uses the same fixed model but disables the later optimization chain. The second
is the current `MasterSkill` pipeline, which allows the system to analyze task
failures, reuse available priors, validate candidate paths, and perform a
limited post-solve optimization pass. For paper consistency, the solved
snapshots in both roots are normalized to `gpt-5.2`.

The paper’s claims are about pipeline behavior under this evaluation protocol.
They are not claims about weight updates, general model pretraining quality, or
unbounded transfer to arbitrary external benchmarks. Similarly, when a task
contains a strong bundled prior, we treat that as part of the environment rather
than evidence of seedless autonomous invention. The paper asks a narrower
question: given a fixed model and realistic external-skill interfaces, can a
benchmark-driven loop improve solve coverage and expose traceable optimization
behavior under official-task evaluation?

## 3. Method: MasterSkill

`MasterSkill` is organized as an iterative loop around benchmark execution. The
pipeline begins with a base attempt, then uses task feedback to decide whether
to reuse an available prior, generate or refine a candidate skill, validate the
candidate in the official environment, and optionally perform a post-solve
optimization pass. The goal is not to maximize unconstrained exploration, but to
preserve only those paths that survive real-task evaluation.

### 3.1 Base Attempt

Each task begins with a direct solve attempt by the fixed model. This step
establishes a reference path: either the task is solved immediately, or the
system gets an initial failure signal under the real execution protocol. The
base attempt is important for two reasons. First, it defines the minimal solve
path that later optimizations should beat or preserve. Second, it prevents the
pipeline from attributing every success to downstream skill machinery when some
tasks are already solvable without further intervention.

### 3.2 Task Analysis And Prior Access

If the base attempt fails or if the system enters a post-solve optimization
phase, `MasterSkill` analyzes the task and inspects available priors. These
priors can include task-local bundled skills, previously derived skills, or
candidate procedures produced during earlier runs. This stage is deliberately
prior-aware: if an executable task-local pipeline already exists, the system
should prefer validating and adapting that path before inventing a new one from
scratch.

This design choice is central to the paper’s claim boundary. In our strongest
case, `taxonomy-tree-merge`, the paper does not claim autonomous invention of
the core taxonomy method. Instead, it claims that the benchmark-driven loop can
recognize, preserve, validate, and operationalize a strong bundled prior under
official-task discipline.

### 3.3 Candidate Generation And Refinement

When existing priors are insufficient, or when a solved path appears overly
expensive, the system can construct or refine candidate skills. These candidates
may target cleaner execution, smaller effective token use, or a more reusable
procedure. Crucially, candidate generation is not accepted at face value. A
candidate skill is only meaningful if it improves or preserves the actual solve
path once it is run in the task environment.

### 3.4 Official-Task Validation

Validation is the core filter in `MasterSkill`. Candidate skills are run against
the real task environment and judged by the task’s official success condition.
This matters because many apparently plausible skill compressions fail only when
the full environment is exercised. A shorter prompt, a faster pipeline, or a
cleaner-looking script is not sufficient evidence on its own. What survives is
whatever continues to produce the required artifacts and passes official-task
validation.

### 3.5 Post-Solve Optimization And Candidate Rejection

Even after a task is solved, `MasterSkill` can attempt one limited post-solve
optimization round. This step tests whether the passing path can be made faster,
smaller, or more reusable. The key point is that post-solve optimization is
still bound by official-task validation. If a follow-up candidate fails that
validation step, the system rejects it rather than preserving a cosmetically
attractive but invalid improvement.

This behavior appears clearly in the selected cases. In
`taxonomy-tree-merge`, the system records a solved current path and rejects the
follow-up candidate `taxonomy-tree-merge-fast` when it fails the official real
test. In `enterprise-information-search` and `financial-modeling-qa`, the
pipeline likewise records rejected post-solve candidates, showing that the loop
is not merely a generator of alternative prompts but a validator that actively
filters regressions. In `pddl-tpp-planning`, the event trace shows the opposite
case: an accepted optimization path that improves event-level duration and
effective token usage, even though the top-level suite metric for the task is
not itself a simple runtime win.

Overall, the method should be read as a benchmark-driven control loop for
external skills. It attempts, analyzes, reuses, generates, validates, refines,
and rejects under official-task feedback. The central empirical question is then
whether this loop produces better benchmark outcomes than the frozen baseline,
and whether the resulting improvements are interpretable enough to support
defensible paper claims.

## 4. Experimental Setup

We evaluate `MasterSkill` on a frozen slice of `SkillsBench` containing `15`
tasks. The tasks span heterogeneous real-environment workflows, including
information retrieval, spreadsheet analysis, planning, taxonomy construction,
and other execution-heavy problems. Each task is evaluated through its official
checker or official output contract inside the real task environment. As a
result, the reported outcomes are not text-only judgments, but benchmark records
that depend on producing the required artifacts under the intended runtime
conditions.

The paper compares two paper-facing roots. The baseline root is a
pre-evolution configuration that runs the fixed model without the later skill
optimization loop. The current root uses the present `MasterSkill` pipeline,
including task analysis, prior-aware reuse, candidate validation, and one
limited post-solve optimization round. Both roots are frozen at `15 / 15`
coverage, so every task in the slice has a persisted latest record on both
sides.

For paper consistency, the solved snapshots in the reported baseline and current
roots are normalized to `gpt-5.2`. Historical exploratory runs and archival
probe directories still exist in the repository, but they are not part of the
reported comparison. The paper-facing suite therefore represents a consistent
single-model comparison over the latest baseline/current task records.

Our primary metrics are suite-level solve coverage and per-task solved/unsolved
status. We also inspect runtime and effective token usage, but only with caution.
This is necessary because the current evidence does not support a universal
runtime-win story: some common-solved tasks show event-level optimization
benefits, while their top-level suite durations remain mixed. Accordingly, the
headline quantitative claim in this paper is solve-coverage gain, while runtime
and token findings are treated as task-specific supporting evidence.

## 5. Main Results

The frozen suite comparison supports a clear coverage-gain result. The
paper-facing baseline solves `3 / 15` tasks, while the paper-facing current
pipeline solves `6 / 15`. This yields three solve gains and no solve losses,
moving solve rate from `20.0%` to `40.0%` on the reported slice.

The three solve gains are `taxonomy-tree-merge`, `xlsx-recover-data`, and
`seismic-phase-picking`, but they are not equally informative.
`taxonomy-tree-merge` is the strongest mechanism case because it exposes a
clear failed-to-solved transition, validated output artifacts, and a rejected
regressive candidate. `xlsx-recover-data` is a clean secondary solve gain,
while `seismic-phase-picking` is better treated as a suite-level gain than as a
central explanation case.

The common-solved tasks show why the paper avoids a broad efficiency claim.
`financial-modeling-qa` is a favorable supporting example: the current root is
faster than the paper-facing baseline and uses a much smaller effective token
footprint. By contrast, `enterprise-information-search` remains solved on both
sides but is slower in the current frozen root, despite still exposing useful
post-solve rejection behavior. `pddl-tpp-planning` provides an even sharper
warning against overclaiming: its trace records an accepted optimization with
improved event-level duration and effective token use, yet the top-level current
suite duration is still larger than the baseline snapshot. This distinction
between suite-level and trace-level evidence is central to the paper’s
interpretation.

Taken together, the results support the following reading. First, the current
pipeline is better than the frozen baseline at turning some previously unsolved
tasks into solved tasks under official evaluation. Second, the system exhibits
meaningful post-solve optimization behavior on selected common-solved tasks.
Third, that supporting evidence is heterogeneous enough that it should not be
collapsed into a broad claim of universal efficiency improvement.

## 6. Case Study: Taxonomy Tree Merge

`taxonomy-tree-merge` is the clearest primary case in the current paper because
it combines all of the evidence types that matter for a benchmark-driven
external-skill optimization claim. In the frozen baseline suite, the task
remains unsolved and ends without a passing solve record. In the frozen current
suite, the task is solved under `gpt-5.2`. This establishes a direct
failed-to-solved transition inside the same paper-facing comparison protocol.

The mechanism behind this gain must be described carefully. The safest and most
accurate interpretation is not that `MasterSkill` autonomously invented the key
taxonomy method from scratch. Instead, the task includes a strong bundled prior:
an executable task-local taxonomy pipeline. The current evidence shows that the
benchmark-driven loop can recognize and preserve that prior, validate it in the
real task environment, and convert it into a solved benchmark record under
official-task discipline.

This reading is supported by direct artifact evidence already recorded in the
repository. The task-level pipeline produces the required taxonomy artifacts,
including `unified_taxonomy_full.csv` and `unified_taxonomy_hierarchy.csv`, and
prior validation records show that the official checks pass on those outputs.
In the current frozen run, the solved event occurs on the base attempt with an
event-level duration of `338.07s` and `23410` effective total tokens. The task
therefore does not merely succeed in a synthetic analysis mode; it succeeds
through the actual benchmark pathway.

The post-solve stage strengthens the case further. After the task is solved, the
pipeline attempts a follow-up candidate, `taxonomy-tree-merge-fast`. That
candidate is not accepted. Instead, the run records that it failed the official
real test, and the system rejects it. This rejection behavior is important
because it shows that `MasterSkill` is not simply generating compressed
variants and keeping whichever looks simpler. The control loop preserves
official-task discipline even when a candidate seems like a plausible
optimization.

As a result, `taxonomy-tree-merge` supports a precise claim: `MasterSkill` can
turn a hard task from failed to solved in the frozen suite while leveraging a
bundled prior, validating the resulting path under the official task
environment, and rejecting a regressive candidate. This is why the task should
anchor the paper’s mechanism narrative.

## 7. Supporting Cases

The supporting cases explain what the optimization loop is doing outside the
primary failed-to-solved example. They matter not because they create a second
headline result, but because they show how the system behaves after a solve and
how that behavior should be interpreted.

`financial-modeling-qa` is the cleanest supporting case for a tighter current
solve profile. The task is solved in both roots, but the current paper-facing
record is faster and substantially smaller in effective token usage than the
baseline snapshot. Its current trace shows a solved base attempt followed by a
rejected follow-up candidate, indicating that the system can preserve a good
solve path while still testing and filtering refinements. This task is the best
main-text supporting example for a pragmatic optimization story.

`enterprise-information-search` plays a different role. It is solved in both
roots, and the current frozen record is not a runtime win. Nevertheless, the
trace is still useful because it shows that the post-solve stage continues to
generate and reject regressive candidates under official-task validation. In
other words, the task supports the claim that `MasterSkill` is a
validation-and-filter loop, even when it is not a suite-level efficiency
improvement.

`pddl-tpp-planning` is best treated as appendix-level or secondary supporting
evidence. Its current event trace is genuinely informative: the accepted
real-test skill improves event-level duration from `199.23s` to `148.34s` and
reduces effective tokens from `11722` to `8812`. At the same time, the top-level
current suite duration remains larger than the paper-facing baseline snapshot.
The task therefore demonstrates that event-level optimization can be real even
when top-level suite metrics remain mixed. That makes it valuable, but only if
the paper states the distinction explicitly.

## 8. Limitations

The current paper is deliberately narrow, and that narrowness is a real
limitation rather than a stylistic choice. The reported suite contains only a
frozen `15`-task slice, so the results should not be read as evidence that the
pipeline broadly improves all realistic tool-using benchmarks. The strongest
quantitative result is a solve-coverage gain on this slice, not a claim of
general dominance.

The evidence for efficiency improvement is also mixed. Some tasks, especially
`financial-modeling-qa`, provide useful support for a tighter current solve
profile. Other tasks, such as `enterprise-information-search`, do not. Still
others, such as `pddl-tpp-planning`, show meaningful event-level optimization
without yielding a simple top-level runtime win in the frozen suite record. For
that reason, the paper intentionally avoids a broad runtime-optimization claim.

Many failed tasks also remain weakly classified. A substantial fraction of the
unsolved slice is still labeled `abandoned_without_classification`, which limits
how confidently we can separate fundamental task difficulty from runtime,
environment, or orchestration bottlenecks. This affects the interpretability of
the negative results and constrains how strongly we can generalize from the
observed wins.

Finally, some of the strongest successful cases rely on bundled task-local
priors. This is not a flaw in the benchmark setting, but it does constrain the
claim boundary. In particular, the paper should not present bundled-prior
validation and orchestration improvements as proof of seedless autonomous skill
invention. The strongest current evidence is that benchmark-driven optimization
can leverage, validate, refine, and reject external skill paths under official
feedback. Broader claims about autonomous invention and cross-task transfer
remain future work.

## 9. Conclusion

This paper presents `MasterSkill` as a benchmark-driven external-skill
optimization loop for realistic `SkillsBench` tasks. In the reported frozen
comparison, the current pipeline improves solve coverage from `3 / 15` to
`6 / 15` with no solve losses, supporting a clear suite-level coverage-gain
claim.

The case analysis clarifies why that gain matters. `taxonomy-tree-merge` shows
the clearest end-to-end chain value: a failed baseline becomes a solved current
task through a bundled prior that survives official-task validation, and a
regressive candidate is rejected rather than silently accepted. Supporting tasks
show that the same loop can also evaluate post-solve refinements and preserve
official-task discipline even when the efficiency evidence is mixed.

The resulting picture is intentionally modest but defensible. Benchmark-driven
external skill optimization appears promising, especially as a mechanism for
turning reusable procedures into validated task solutions under real execution
constraints. At the same time, the current evidence is not yet a broad claim of
universal runtime improvement or autonomous method invention. The next step is
to expand the experimental base while preserving the same level of trace-level
interpretability and official-task rigor.
