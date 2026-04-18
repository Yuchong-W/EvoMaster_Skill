# Enterprise Targeted Evidence Writeback

Low-context workflow for enterprise-information-search: parse the three questions, run narrow alias-aware searches over the artifact corpus, verify scope to avoid cross-product leakage, and write verifier-safe answers to /root/answer.json.

## When to Use

Use when the task must answer q1/q2/q3 from /root/question.txt using evidence in /root/DATA and write /root/answer.json under the required JSON contract.

## How to Use

1. Read `/root/question.txt` and extract only the concrete entities, time windows, and requested return type for `q1`, `q2`, and `q3`.
2. For each question, build a minimal alias list from the exact terms in the question plus only renamed/predecessor names discovered in the first relevant hits; do not do broad synonym hunting.
3. Search `/root/DATA` with targeted `rg -n -i` queries against likely artifact folders (`documents`, `slack`, `meeting_transcripts`, `urls`, `prs`). Prefer filename/title search first when the question references doc IDs, PRs, channels, or named artifacts. Open only matched files or short snippets, never the whole corpus.
4. Accept a candidate only if its surrounding context matches the question's product/team/date scope. Reject sibling products, stale aliases that now refer elsewhere, and generic mentions without grounding. Normalize the final result to a deduplicated list of strings or IDs.
5. Write `/root/answer.json` exactly as a dict with keys `q1`, `q2`, `q3`. Each value must be an object with `answer` and `tokens`. `answer` must always be a list, even for a single item. `tokens` must be a positive numeric value, not a string; if exact per-question counts are unavailable, reuse a positive run estimate consistently.
6. Finalization checklist before exit: reopen `/root/answer.json`, parse it as JSON, ensure `q1`/`q2`/`q3` all exist, every `answer` is a list, every `tokens` is numeric and > 0, and nothing is truncated or missing. Run the validator script on `/root/answer.json` if available.

## Scripts

### validate_answer_contract.py

```
import json
import sys
from pathlib import Path

EXPECTED = ("q1", "q2", "q3")


def fail(msg: str) -> int:
    print(msg)
    return 1


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) == 2 else "/root/answer.json")
    if not path.exists():
        return fail(f"missing file: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid json: {exc}")

    if not isinstance(payload, dict):
        return fail("answer payload is not a dict")

    for key in EXPECTED:
        if key not in payload:
            return fail(f"missing key: {key}")
        entry = payload[key]
        if not isinstance(entry, dict):
            return fail(f"{key} entry is not a dict")
        if "answer" not in entry or "tokens" not in entry:
            return fail(f"{key} missing answer or tokens")
        if not isinstance(entry["answer"], list):
            return fail(f"{key}.answer is not a list")
        tokens = entry["tokens"]
        if not isinstance(tokens, (int, float)):
            return fail(f"{key}.tokens is not numeric")
        if tokens <= 0:
            return fail(f"{key}.tokens must be positive")

    print("answer contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

```

