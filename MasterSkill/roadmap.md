# MasterSkill Roadmap

Updated: 2026-04-18

## Why This Plan Is Right

The current project should not jump directly into a paper-only agenda.

The stronger route is:

1. first make `MasterSkill` a real, publishable open-source system on `SkillsBench`
2. then use that stabilized system as the base for the more ambitious research agenda

This separation matters because the project is currently proving different kinds of gains at once:

- harness and runtime recovery
- better leverage of existing task-local skills
- research-derived skill improvement on some tasks

If these are mixed into one claim too early, both the OSS story and the paper story become weak.

The plan below therefore splits the work into two phases:

- `Phase 1`: ship a high-quality OSS system with full-suite evidence
- `Phase 2`: build seedless skill construction on top of that system and package the paper claim

## Phase 1 Goal: Publishable OSS

### Target Outcome

Release `MasterSkill` as a benchmark-driven skill runtime that can:

- solve a meaningful portion of `hard` `SkillsBench` tasks, even when solving them is expensive
- make `medium` and `easy` tasks cheaper, faster, and more stable
- run at full-suite scale with reproducible artifacts and clear evaluation outputs

This phase is complete when the repo is good enough that an external user can:

- install it
- understand the runtime architecture
- run at least a meaningful subset locally
- reproduce the reported full-suite evaluation with the documented commands

### Product Claim For Phase 1

`MasterSkill` is a practical benchmark-driven runtime for external skill use and skill refinement on `SkillsBench`.

The Phase 1 claim is intentionally narrower than a paper claim:

- it does not require seedless skill discovery
- it does not require claiming that research always invents new knowledge
- it only requires that the system is useful, stable, and benchmark-credible

### Core Evaluation Standard

The main evaluation target for Phase 1 is at least one frozen full `SkillsBench` sweep.

That sweep must include:

- a `current/evolved` run
- the required baseline variant(s), especially the pure pre-evolution baseline where relevant
- persisted benchmark artifacts under the repository data roots

The full-suite run is the main evidence.

Small subsets are still useful, but only as calibration and optimization tools before the frozen sweep.

### Phase 1 Success Criteria

#### A. Hard Tasks

For `hard` tasks, success means:

- some tasks that are difficult enough to resist direct expert-skill application can now be passed by the current chain
- these passes are real official-test passes, not judge-only wins
- expensive solves are acceptable in this phase if they are stable and reproducible

What matters most here is coverage expansion and credible solve paths, not immediate cost efficiency.

#### B. Medium And Easy Tasks

For `medium` and `easy` tasks, success means:

- stable pass rate
- lower runtime
- lower `effective_total_tokens`
- fewer harness-induced failures

What matters most here is operational quality, not novelty.

#### C. System Quality

The runtime must be stable enough that:

- long unattended runs do not frequently die from avoidable harness failures
- result persistence is complete and analyzable
- the same configuration can be frozen and rerun
- failure classes are interpretable

#### D. Open-Source Readiness

The repo must have:

- a clean install path
- quickstart instructions
- clear benchmark commands
- documented data-root behavior
- artifact hygiene and ignore rules
- reproducibility notes and known limits

## Phase 1 Workstreams

### 1. Runtime Stabilization

Continue improving:

- Docker build reliability
- artifact export correctness
- internal-agent timeout and fallback behavior
- research-loop termination and budgeting
- official-test isolation and execution fidelity

This work should be judged by whether it improves full-suite reliability, not by whether it is elegant in isolation.

### 2. Full-Suite Evaluation Infrastructure

Before the frozen full run:

- choose the exact Phase 1 config
- freeze key budgets and routing behavior
- document the command surface for full-suite execution
- ensure result storage is complete for:
  - pass/fail
  - duration
  - raw tokens
  - cached tokens
  - effective tokens
  - failure class

After the frozen full run:

- generate a compact result summary table
- generate a failure breakdown table
- generate a comparison view between baseline and current/evolved

### 3. Attribution Layer

Phase 1 still needs attribution, even if it is not yet the full paper story.

Each meaningful success should be classified as primarily one of:

- `harness recovery`
- `bundled-skill leverage`
- `research-derived accepted skill`
- `mixed / unclear`

This prevents overclaiming and creates the base for Phase 2.

### 4. OSS Packaging

The repository should be upgraded from internal lab layout to release-quality layout.

Required deliverables:

- polished top-level `README.md`
- `MasterSkill/readme.md` aligned with the actual runtime
- a formal roadmap
- install instructions
- quickstart with one or two realistic commands
- evaluation guide
- reproducibility guide
- explanation of result files and data directories

### 5. Release Discipline

Do not keep changing the runtime while collecting the final Phase 1 evidence.

Use this sequence:

1. optimize on calibration tasks
2. freeze the Phase 1 config
3. run the full suite
4. summarize the results
5. only then prepare the release tag

## Phase 1 Release Checklist

The OSS milestone should not be declared complete until the following are true:

- `SkillsBench` has been run end-to-end at least once with a frozen Phase 1 configuration
- `current/evolved` outputs are persisted and analyzable
- required baseline outputs are persisted and analyzable
- hard-task case studies exist and point to real official-test passes
- medium/easy-task summaries show runtime, token, or stability gains
- the top-level docs match the actual commands and layout
- failed post-pass artifacts and transient skill candidates are not polluting the repo
- a new user can understand the main execution path from docs alone

## Phase 2 Goal: Seedless Skill Construction

### Target Outcome

After Phase 1, extend `MasterSkill` so that it can start without task-local seed skills and still:

- research task-relevant knowledge
- synthesize a usable skill
- validate that skill through the normal runtime
- optimize the successful skill for lower cost and runtime

This is the phase with real top-tier paper potential.

### Research Claim For Phase 2

On top of a stable benchmark runtime, `MasterSkill` can automatically construct, validate, and optimize external skills for hard tasks even without task-local seed skills.

This is a much stronger claim than Phase 1 and should only be made after the OSS base is stable.

### Why Phase 2 Must Come After Phase 1

Without the Phase 1 base, seedless experiments will be confounded by:

- harness instability
- incomplete persistence
- unclear attribution
- missing reproducibility

That would make it too easy for reviewers to argue that any gain came from system repair rather than automated skill construction.

### Phase 2 Experimental Axes

At minimum, Phase 2 should compare:

- `with seed skill` vs `without seed skill`
- `research enabled` vs `research disabled`
- `raw discovered skill` vs `optimized discovered skill`
- `single-task success` vs `transfer to related tasks`

The point is not merely to show a single pass.

The point is to show a causal chain:

1. no useful seed skill is available
2. research creates or composes new usable knowledge
3. the runtime turns that knowledge into a passing skill-guided solve path
4. post-pass optimization reduces cost without destroying correctness

### Phase 2 Success Criteria

This phase is complete when there are enough examples to show that:

- seedless discovery is real, not anecdotal
- the discovered skills survive official tests
- optimized versions preserve correctness while reducing cost
- the gains are not better explained by harness fixes or hidden bundled priors

## Recommended Sequencing

### Milestone A: Current-Chain Stabilization

Focus on:

- runtime stability
- data persistence
- failure classification
- loop termination
- artifact correctness

Deliverable:

- calibration tasks are stable enough for long runs

### Milestone B: Full-Suite Frozen Run

Focus on:

- frozen configuration
- full `SkillsBench` execution
- complete result capture

Deliverable:

- one credible full-suite benchmark snapshot

### Milestone C: OSS Release Candidate

Focus on:

- documentation
- examples
- release packaging
- result summary tables

Deliverable:

- public-facing open-source release candidate

### Milestone D: Seedless Mode

Focus on:

- disabling task-local seed-skill dependence
- strengthening research-to-skill synthesis
- validating discovered skills through the same execution chain

Deliverable:

- seedless experimental mode with persisted outputs

### Milestone E: Paper Evidence

Focus on:

- attribution
- ablations
- case studies
- transfer evidence

Deliverable:

- paper-ready empirical package

## What Not To Do

- Do not claim seedless skill construction before the runtime base is stable.
- Do not use a small task subset as the final Phase 1 evidence.
- Do not mix calibration runs with frozen evaluation runs.
- Do not treat every success as a research-generated skill success.
- Do not optimize for prompt beauty or Judger satisfaction when official tests disagree.

## Immediate Next Steps

1. finish stabilizing the current chain on calibration tasks
2. define the exact frozen Phase 1 configuration for the full-suite run
3. execute at least one full `SkillsBench` sweep
4. summarize the suite-level results and attribution categories
5. prepare the OSS release candidate
6. then begin seedless-skill construction work as Phase 2

## Bottom Line

The best path is:

- first, prove `MasterSkill` is a real and useful open-source benchmark runtime
- second, use that runtime to pursue seedless skill construction as the paper-defining contribution

That ordering maximizes both practical value and research credibility.
