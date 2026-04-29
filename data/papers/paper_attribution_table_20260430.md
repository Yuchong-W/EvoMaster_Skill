# MasterSkill Attribution Table Draft

Date: 2026-04-30

## Selected Tasks

| Task | Frozen Suite Outcome | Provisional Attribution | Why This Label |
|---|---|---|---|
| taxonomy-tree-merge | baseline failed, current solved | coverage gain + bundled-skill leverage + chain validation | best failed-to-solved case; executable bundled pipeline; official outputs confirmed; regressive post-pass candidate rejected |
| xlsx-recover-data | baseline failed, current solved | coverage gain, exact mechanism still unclear | real solve gain in frozen compare; needs more chain-level explanation before writing a strong mechanism claim |
| seismic-phase-picking | baseline failed, current solved | coverage gain, but mechanism still thin | fresh `gpt-5.2` rerun solved from base attempt and rejected a follow-up candidate; useful for suite metrics, weaker for innovation attribution |
| enterprise-information-search | solved in both, current slower | post-pass optimization evidence, not suite-level efficiency gain | historical docs record accepted optimized skills and large gains; the fresh gpt-5.2 rerun still solves and now also records a rejected follow-up candidate |
| financial-modeling-qa | solved in both, current slightly faster | compact accepted optimization | fresh gpt-5.2 rerun still solves and records a rejected optimized candidate, making it a clean supporting optimization case |
| pddl-tpp-planning | solved in both | accepted optimization evidence | fresh gpt-5.2 rerun records an accepted optimized candidate with lower event-level duration and lower effective tokens |
| react-performance-debugging | failed in both frozen roots | mixed / unclear | useful as pipeline-debugging context only |
| speaker-diarization-subtitles | failed in both frozen roots | mixed / unclear | current latest persisted after host-side interrupt; not a positive paper result |
| video-filler-word-remover | failed in both frozen roots | mixed / unclear | current latest persisted after host-side interrupt; not a positive paper result |

## Current Paper Use

Recommended:

- main suite table:
  - all 15 tasks
- primary case study:
  - `taxonomy-tree-merge`
- supporting task discussion:
  - `enterprise-information-search`
  - `financial-modeling-qa`
- optional second solve-gain mention:
  - `xlsx-recover-data`
  - `seismic-phase-picking`

Avoid as central positive evidence:

- `pddl-tpp-planning`
- `react-performance-debugging`
- `speaker-diarization-subtitles`
- `video-filler-word-remover`
