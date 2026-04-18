# MasterSkill Case Tasks

This directory is the local case root for tasks under active evolution.

Layout:

- `tasks/pddl-tpp-planning`
- `tasks/taxonomy-tree-merge`
- `tasks/xlsx-recover-data`
- `tasks/react-performance-debugging`
- `tasks/financial-modeling-qa`
- `tasks/latex-formula-extraction`
- `tasks/quantum-numerical-simulation`
- `tasks/enterprise-information-search`
- `tasks/video-filler-word-remover`
- `tasks/speaker-diarization-subtitles`
- `tasks/gravitational-wave-detection`
- `tasks/shock-analysis-supply`
- `tasks/shock-analysis-demand`
- `tasks/seismic-phase-picking`
- `tasks/reserves-at-risk-calc`

The runtime now prefers this local case root by default, so ongoing skill research
and task-local skill writes happen here before touching the original external
`/home/yuchong/skillsbench` tree.

Selection notes:

- Current active loop-validation targets:
  - `pddl-tpp-planning`
  - `xlsx-recover-data`
  - `taxonomy-tree-merge`
- Additional hard zero-pass cases copied in for broader optimization:
  - `react-performance-debugging`
  - `financial-modeling-qa`
  - `latex-formula-extraction`
  - `quantum-numerical-simulation`
  - `enterprise-information-search`
- Additional multi-modal and scientific zero-pass cases now staged locally:
  - `video-filler-word-remover`
  - `speaker-diarization-subtitles`
  - `gravitational-wave-detection`
  - `shock-analysis-supply`
  - `shock-analysis-demand`
  - `seismic-phase-picking`
  - `reserves-at-risk-calc`
- Deferred for now because they depend more directly on external auth / network-specific setup:
  - `gh-repo-analytics`
  - `scheduling-email-assistant`
