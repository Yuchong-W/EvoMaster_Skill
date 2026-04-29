# MasterSkill Frozen Results Table Draft

Date: 2026-04-30

## Main Comparison

| Task | Baseline | Current | Baseline Dur. (s) | Current Dur. (s) | Result Type | Provisional Attribution |
|---|---|---:|---:|---:|---|---|
| enterprise-information-search | solved | solved | 249.18 | 807.26 | common-solved | post-pass optimization evidence, but not a runtime win |
| financial-modeling-qa | solved | solved | 630.63 | 554.75 | common-solved | compact optimization evidence with cleaner token profile |
| gravitational-wave-detection | abandoned | abandoned | 694.20 | 361.76 | unchanged-failure | unclear |
| latex-formula-extraction | abandoned | abandoned | 1357.92 | 222.35 | unchanged-failure | likely harness/runtime recovery, not a paper headline |
| pddl-tpp-planning | solved | solved | 160.77 | 652.57 | common-solved | accepted optimization evidence at event level, but not a suite-level runtime win |
| quantum-numerical-simulation | abandoned | abandoned | 1587.02 | 1500.58 | unchanged-failure | unclear |
| react-performance-debugging | abandoned | abandoned | 589.65 | 692.69 | unchanged-failure | useful only as runtime-debugging context |
| reserves-at-risk-calc | abandoned | abandoned | 1107.53 | 1498.43 | unchanged-failure | unclear |
| seismic-phase-picking | abandoned | solved | 725.66 | 1276.95 | solve-gain | new solve gain after strict `gpt-5.2` rerun; real but not the clearest mechanism case |
| shock-analysis-demand | abandoned | abandoned | 680.67 | 1498.06 | unchanged-failure | unclear |
| shock-analysis-supply | abandoned | abandoned | 280.08 | 1498.63 | unchanged-failure | unclear |
| speaker-diarization-subtitles | abandoned | abandoned | 170.21 | 718.21 | unchanged-failure | current snapshot persisted after host-side interrupt |
| taxonomy-tree-merge | abandoned | solved | 300.47 | 1028.40 | solve-gain | strongest primary case; bundled executable skill + chain validation |
| video-filler-word-remover | abandoned | abandoned | 126.93 | 201.39 | unchanged-failure | current snapshot persisted after host-side interrupt |
| xlsx-recover-data | abandoned | solved | 370.94 | 872.94 | solve-gain | secondary coverage-gain case |

## Aggregate Summary

| Metric | Baseline | Current |
|---|---:|---:|
| Tasks compared | 15 | 15 |
| Solved tasks | 3 | 6 |
| Solve rate | 20.0% | 40.0% |
| Solve gains | - | 3 |
| Solve losses | - | 0 |
| Common-solved tasks | 3 | 3 |
| Current faster on common-solved | - | 1 |
| Current lower effective tokens on common-solved | - | 1 |

## Reading Guide

- The strongest suite-level claim is solve coverage gain, not broad efficiency gain.
- `taxonomy-tree-merge` is the strongest primary case study.
- `xlsx-recover-data` is the cleanest second solve-gain case in the frozen compare.
- `seismic-phase-picking` is now also a solve gain, but it is better treated as a secondary suite result than as a mechanism case.
- `enterprise-information-search` and `financial-modeling-qa` are better used as supporting examples than as headline suite-level gains.

## Evidence Hygiene Note

The paper-facing `latest` suite has been normalized to `gpt-5.2`.

- current-side solved latest snapshots have been replaced by `gpt-5.2`
- baseline-side solved latest snapshots have been replaced in the same way
- historical logs and archival probe directories still contain older
  pre-normalization runs, but they are not part of the frozen paper comparison
