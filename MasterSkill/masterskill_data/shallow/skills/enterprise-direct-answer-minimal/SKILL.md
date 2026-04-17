# Enterprise Minimal Evidence Answer

Answers `q1`/`q2`/`q3` from `/root/question.txt` against `/root/DATA` with narrow alias-aware retrieval, minimal evidence capture, and deterministic finalization into verifier-safe `/root/answer.json`.

## When to Use

Use for `enterprise-information-search` when the task requires writing `/root/answer.json` with answers for `q1`, `q2`, and `q3`, especially when product names may have historical aliases or the evidence is split across docs, PRs, chats, meetings, or URLs.

## How to Use

1. Read `/root/question.txt` and extract `q1`, `q2`, and `q3` exactly.
2. Solve one question at a time to keep context small. For the current question, note only: target entity, requested field, any time/version constraint, and 2-4 likely aliases.
3. Start with direct search on `/root/DATA` using `rg` for `alias + field keyword`. Use `enterprise-alias-evidence-search` first for alias pivots. Open only the few candidate artifacts that can directly prove the answer.
4. Prefer authoritative proof in this order: docs/PRs/URLs, then chats/meetings only for alias bridging or when no final artifact exists. Reject hits that do not clearly map to the same entity.
5. Keep the smallest possible evidence set: 1-2 short snippets per question, only enough to justify the answer and estimate tokens. While solving, store a draft in `/root/answer.json` as `{"q1":{"answer":[...],"_evidence":[...]},"q2":...,"q3":...}`. Always keep `answer` as a list, even for one item.
6. If a question is unresolved, add one alias or predecessor name from the strongest hit and rerun a narrow search. Use `enterprise-artifact-search` only if direct alias-led retrieval still leaves a multi-hop gap. Do not broad-scan the corpus once alias/doc/URL pivots are exhausted.
7. Run `python scripts/finalize_answers.py /root/question.txt /root/answer.json` to replace the draft with the final verifier-safe JSON containing only `answer` and numeric `tokens`.
8. Finalization checklist before exit: reopen `/root/answer.json`; parse it; confirm keys `q1`, `q2`, `q3` exist; confirm each entry contains only `answer` and `tokens`; confirm every `answer` is a list; confirm every `tokens` value is numeric and `> 0`; print the final validated JSON exactly with no extra narration.

## Scripts

### scripts/finalize_answers.py

```
import json
import math
import re
import sys
from pathlib import Path

KEYS = ("q1", "q2", "q3")
LINE_RE = re.compile(r'"(q[123])"\s*:\s*(.+?)(?:,)?$')


def load_questions(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {k: str(data.get(k, "")) for k in KEYS}
    except Exception:
        pass
    out = {}
    for line in text.splitlines():
        m = LINE_RE.search(line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip().rstrip(",")
    return out


def as_list(value):
    return value if isinstance(value, list) else [value]


def evidence_text(entry):
    raw = entry.get("_evidence", "")
    if isinstance(raw, list):
        return "\n".join(str(x) for x in raw)
    return str(raw)


def estimate_tokens(question_text, answers, evidence):
    blob = question_text + "\n" + json.dumps(answers, ensure_ascii=False) + "\n" + evidence
    return max(1, int(math.ceil(len(blob) / 4.0) + 64))


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("answer payload is not a dict")
    for key in KEYS:
        if key not in payload:
            raise ValueError(f"missing key: {key}")
        entry = payload[key]
        if not isinstance(entry, dict):
            raise ValueError(f"{key} entry is not a dict")
        if set(entry.keys()) != {"answer", "tokens"}:
            raise ValueError(f"{key} must contain only answer and tokens")
        if not isinstance(entry["answer"], list):
            raise ValueError(f"{key}.answer is not a list")
        if not isinstance(entry["tokens"], int) or entry["tokens"] <= 0:
            raise ValueError(f"{key}.tokens must be a positive int")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: finalize_answers.py <question.txt> <answer.json>")

    question_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])
    questions = load_questions(question_path)
    draft = json.loads(answer_path.read_text(encoding="utf-8"))

    final_payload = {}
    for key in KEYS:
        entry = draft.get(key)
        if not isinstance(entry, dict):
            raise ValueError(f"{key} entry is not a dict")
        answers = as_list(entry.get("answer"))
        final_payload[key] = {
            "answer": answers,
            "tokens": estimate_tokens(questions.get(key, ""), answers, evidence_text(entry)),
        }

    rendered = json.dumps(final_payload, ensure_ascii=False, indent=2)
    answer_path.write_text(rendered, encoding="utf-8")
    reopened = json.loads(answer_path.read_text(encoding="utf-8"))
    validate(reopened)
    print(json.dumps(reopened, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

```

