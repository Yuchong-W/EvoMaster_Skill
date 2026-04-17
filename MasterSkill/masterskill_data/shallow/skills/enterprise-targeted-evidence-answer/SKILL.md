# Enterprise Targeted Evidence Answer

Answers `enterprise-information-search` with a narrow, alias-aware retrieval loop over `/root/DATA`, then writes a verifier-safe `/root/answer.json` with list-normalized answers and deterministic numeric token estimates.

## When to Use

Use when the task asks for answers to `q1`, `q2`, and `q3` from `/root/question.txt` using enterprise artifacts in `/root/DATA`, especially when entities may appear under old names, renamed channels, legacy doc IDs, or mixed artifact types.

## How to Use

1. Read `/root/question.txt` first and extract, for each question, only the target entity, requested field, time/person/product constraints, and likely aliases.
2. Do targeted retrieval instead of corpus-wide reading: search `/root/DATA` by the strongest anchors first (exact product/person/org names, doc IDs, channel names, ticket IDs), then expand to 2-5 plausible aliases only if the first pass is incomplete.
3. Search across artifact types that commonly hold enterprise evidence (`documents`, `slack`, `meeting_transcripts`, `urls`, `prs`) and keep only snippets that directly answer the requested field. Reject near-name distractors and cross-product leakage.
4. For each question, stop once you have one consistent answer set backed by concrete evidence from the artifacts. Prefer exact IDs/names/titles over summaries. If multiple items are explicitly supported, return all of them; otherwise return one-item list.
5. Write `/root/answer.json` as a dict with exactly `q1`, `q2`, `q3`, each shaped as `{"answer": [...], "tokens": <number>}`. `answer` must always be a list, even for a single item.
6. Run the finalization script to compute deterministic token estimates from the actual question text plus serialized answers, rewrite the JSON cleanly, reopen it, parse it, and fail fast on missing keys, wrong types, empty/truncated output, or invalid JSON.
7. Finalization checklist before exit: ensure `/root/answer.json` exists; reopen it; `json.load` succeeds; keys `q1/q2/q3` all exist; every `answer` is a list; every `tokens` is positive numeric; no entry is missing or truncated.

## Scripts

### finalize_answer.py

```
import json
import math
import re
import sys
from pathlib import Path

QUESTION_RE = re.compile(r'"(q[123])"\s*:\s*(.+?)(?:,)?$')


def parse_questions(path: Path) -> dict[str, str]:
    questions: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        match = QUESTION_RE.search(raw_line.strip())
        if match:
            key, text = match.groups()
            questions[key] = text.strip().rstrip(',')
    return questions


def estimate_tokens(question_text: str, answers: list[str]) -> int:
    blob = json.dumps(answers, ensure_ascii=False, separators=(',', ':'))
    chars = len(question_text) + len(blob)
    return max(32, int(math.ceil(chars / 4.0)) + 48)


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: finalize_answer.py <question.txt> <answer.json>')
        return 2

    question_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])

    if not question_path.exists():
        print(f'missing question file: {question_path}')
        return 1
    if not answer_path.exists():
        print(f'missing answer file: {answer_path}')
        return 1

    questions = parse_questions(question_path)
    payload = json.loads(answer_path.read_text(encoding='utf-8'))

    if not isinstance(payload, dict):
        raise ValueError('answer payload is not a dict')

    normalized = {}
    for key in ('q1', 'q2', 'q3'):
        entry = payload.get(key)
        if not isinstance(entry, dict):
            raise ValueError(f'{key} entry is not a dict')
        answers = entry.get('answer')
        if not isinstance(answers, list):
            raise ValueError(f'{key}.answer is not a list')
        normalized_answers = []
        for item in answers:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized_answers.append(text)
        normalized[key] = {
            'answer': normalized_answers,
            'tokens': estimate_tokens(questions.get(key, ''), normalized_answers),
        }

    encoded = json.dumps(normalized, ensure_ascii=False, indent=2)
    answer_path.write_text(encoded, encoding='utf-8')

    reparsed = json.loads(answer_path.read_text(encoding='utf-8'))
    for key in ('q1', 'q2', 'q3'):
        if key not in reparsed:
            raise ValueError(f'missing key: {key}')
        if not isinstance(reparsed[key].get('answer'), list):
            raise ValueError(f'{key}.answer is not a list after rewrite')
        if not isinstance(reparsed[key].get('tokens'), (int, float)) or reparsed[key]['tokens'] <= 0:
            raise ValueError(f'{key}.tokens invalid after rewrite')

    print('answer contract OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

```

