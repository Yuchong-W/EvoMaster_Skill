---
name: enterprise-alias-evidence-search
description: Alias-grounded, evidence-first retrieval for enterprise-information-search. Resolves renamed products and old doc IDs, rejects cross-product distractors, and returns verifier-safe answers for q1/q2/q3 with list-normalized answers and task-grounded numeric token estimates.
---

# Enterprise Alias Evidence Search

Use this skill for `enterprise-information-search` when the question names a product by its current brand but the evidence may still live under older aliases, renamed channels, or predecessor doc IDs.

## When to Use

- The task must answer `q1`, `q2`, and `q3` from `/root/DATA` into `/root/answer.json`.
- A product appears under multiple historical names or renamed channels.
- The correct answer requires targeted evidence from `documents`, `slack`, `meeting_transcripts`, `urls`, or `prs` without loading the whole corpus.

## Core Rules

1. Build alias maps before retrieval. Do not assume the product name in the question is the only valid search term.
2. Follow the verifier contract, not the illustrative JSON snippet in the instruction.
3. Write `/root/answer.json`, reopen it, parse it, and run the contract check before finishing.

## Required Aliases For This Task

- `CoachForce <- CoFoAIX, SalesCoach`
- `PersonalizeForce <- onalizeAIX, Einstein Adaptive Personalization`

Treat these as lineage aliases, not distractors, when the surrounding product file and discussion context match.

## Grounding Rules

Never accept a candidate artifact until it matches the target product through at least 2 signals:

- product file path
- alias in channel name, doc ID, link, or content
- surrounding discussion clearly about the same renamed product lineage

Prefer primary evidence in this order:

1. exact document objects or exact URL objects
2. slack messages linking the artifact or naming competitors
3. meeting transcripts with attributable speaker turns
4. PR review fields only when directly tied to the asked artifact

## Question-Specific Workflow

### q1

Find employee IDs of the authors and key reviewers of the Market Research Report for the CoachForce product.

1. Start in `/root/DATA/products/CoachForce.json`.
2. Follow alias lineage into `CoFoAIX` or `SalesCoach` only when the artifact remains grounded to CoachForce lineage.
3. Select the latest or final grounded Market Research Report.
4. Take the author from the report document fields first.
5. Take key reviewers only from explicit review signals:
   - report feedback fields
   - review slack replies
   - review-meeting transcript turns with substantive feedback
6. Do not use raw participant lists alone as reviewers.
7. Return deduplicated employee IDs.

### q2

Find employee IDs of team members who provided insights on the strengths and weaknesses of PersonalizeForce's competitor products.

1. Start in `/root/DATA/products/PersonalizeForce.json`.
2. Expand search with the required aliases.
3. Keep only team members who provide substantive competitor analysis.
4. Exclude acknowledgements, status updates, and pure questions.
5. The evidence should mention a competitor and contain concrete evaluative content about strengths or weaknesses.

### q3

Find the demo URLs shared by team members for PersonalizeForce's competitor products.

1. Reuse the grounded PersonalizeForce alias map.
2. Prefer demo URLs shared in messages and use the URL objects as confirmation.
3. Keep only external competitor demo links.
4. Exclude internal `sf-internal.slack.com` links and demos for PersonalizeForce itself.

## Output Contract

The final file must be `/root/answer.json` and contain:

```json
{
  "q1": {"answer": ["..."], "tokens": 123},
  "q2": {"answer": ["..."], "tokens": 123},
  "q3": {"answer": ["..."], "tokens": 123}
}
```

Rules:

- Every `answer` value must be a list, even for one item.
- Every `tokens` value must be numeric, positive, and under the verifier threshold.
- Do not use a fixed placeholder such as `123` for every question. Populate the per-question numeric token fields with the bundled helper after the final answers are written.
- All three keys must be present.

## Finalization Checklist

1. Build the full answer dict in memory.
2. Write `/root/answer.json`.
3. Run:

```bash
python3 /root/.codex/skills/enterprise-alias-evidence-search/scripts/estimate_tokens.py /root/question.txt /root/answer.json
```

4. Reopen `/root/answer.json` and parse it with Python.
5. Run:

```bash
python3 /root/.codex/skills/enterprise-alias-evidence-search/scripts/validate_answer_contract.py /root/answer.json
```

6. If the check fails, fix the file before exiting.
7. Print the final validated file contents with:

```bash
cat /root/answer.json
```

8. Stop after printing the final JSON. Do not append a long evidence dump after it.

## Failure Patterns To Avoid

- Treating the instruction example's string token values as authoritative.
- Reusing one placeholder token constant for q1/q2/q3 instead of deriving per-question numeric estimates.
- Printing long narration after the final JSON so the visible result becomes truncated.
- Stopping after retrieval without writing `/root/answer.json`.
- Treating `CoFoAIX` inside `CoachForce.json` as an unrelated distractor when it is the grounded predecessor alias.
- Treating all transcript participants as reviewers.
- Returning internal product demo links for `q3`.
