# Supporting Cases Draft

Date: 2026-05-01

## Purpose

These notes are for the non-primary tasks that help explain what the optimization
chain is doing without forcing the paper to overclaim broad suite-level
efficiency wins.

## Enterprise Information Search

Frozen suite status:

- baseline: `solved`
- current: `solved`

Current latest trace:

- base attempt solved under `gpt-5.2`
- base-attempt duration: `467.77s`
- post-pass candidate: `enterprise-q123-min-cost-retrieval`
- post-pass outcome: rejected by official real test

Use in paper:

- supports the claim that the pipeline continues to test and reject regressive
  follow-up candidates after a solve
- does not support a headline runtime-win claim in the frozen suite

Recommendation:

- mention in supporting-case section, not in the headline result claim

## Financial Modeling QA

Frozen suite status:

- baseline: `solved`
- current: `solved`

Paper-facing comparison:

- baseline duration: `630.63s`
- current duration: `554.75s`
- baseline effective total tokens: `65667`
- current effective total tokens: `30613`

Current latest trace:

- base attempt solved under `gpt-5.2`
- base-attempt duration: `286.73s`
- post-pass candidate: `financial-modeling-pairwise-match-delta-optimized`
- post-pass outcome: rejected by official real test

Use in paper:

- cleanest supporting example for a tighter current solve profile
- useful for showing that optimization pressure can reduce solve cost while
  still preserving evaluation discipline

Recommendation:

- include in main supporting-case section

## PDDL TPP Planning

Frozen suite status:

- baseline: `solved`
- current: `solved`

Paper-facing comparison:

- baseline duration: `160.77s`
- current duration: `652.57s`

Current latest trace:

- base attempt solved under `gpt-5.2` in `199.23s`
- accepted real-test skill: `pddl-tpp-solve-verify-minimal-v2`
- accepted event duration: `148.34s`
- accepted event effective tokens: `8812`
- note records:
  - `duration 199.23s -> 148.34s`
  - `effective_tokens 11722 -> 8812`
  - `skill_md_size regressed 1066 -> 5104`

Use in paper:

- strong event-level optimization example
- weaker suite-level example because top-level current duration is still larger

Recommendation:

- use as optional supporting evidence or appendix example
- do not present it as a simple overall runtime win

## Section-Level Recommendation

Main paper supporting cases:

- `financial-modeling-qa`
- `enterprise-information-search`

Appendix or brief supporting mention:

- `pddl-tpp-planning`
- `seismic-phase-picking`
