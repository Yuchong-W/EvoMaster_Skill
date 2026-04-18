import json
import math
import re
import sys
from pathlib import Path

EXPECTED = ("q1", "q2", "q3")
LINE_RE = re.compile(r'"(q[123])"\s*:\s*(.+?)(?:,)?$')


def clean_question_value(raw: str) -> str:
    value = raw.strip().rstrip(",")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value.strip()


def parse_questions(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        parsed = {}
        for key in EXPECTED:
            if key in data:
                parsed[key] = str(data[key]).strip()
        if parsed:
            return parsed

    parsed = {}
    for line in text.splitlines():
        match = LINE_RE.search(line.strip())
        if match:
            parsed[match.group(1)] = clean_question_value(match.group(2))
    return parsed


def normalize_answers(value):
    if value is None:
        items = []
    elif isinstance(value, list):
        items = value
    else:
        items = [value]

    normalized = []
    seen = set()
    for item in items:
        if isinstance(item, bool) or not isinstance(item, (str, int, float)):
            raise ValueError("answers must contain only strings or numbers")
        if isinstance(item, str):
            item = item.strip()
            if not item:
                continue
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            normalized.append(item)
    return normalized


def normalize_evidence(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("_evidence must be a list when present")
    out = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def estimate_tokens(question: str, answers: list, evidence: list[str]) -> int:
    blob = json.dumps(
        {"question": question, "answer": answers, "evidence": evidence},
        ensure_ascii=False,
        sort_keys=True,
    )
    return max(1, math.ceil(len(blob) / 4.0))


def coerce_entry(value):
    if isinstance(value, dict):
        return value
    return {"answer": value}


def finalize_payload(questions: dict[str, str], payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("answer payload must be a JSON object")

    final = {}
    for key in EXPECTED:
        if key not in payload:
            raise ValueError(f"missing key: {key}")
        entry = coerce_entry(payload[key])
        answers = normalize_answers(entry.get("answer"))
        evidence = normalize_evidence(entry.get("_evidence"))
        final[key] = {
            "answer": answers,
            "tokens": estimate_tokens(questions.get(key, ""), answers, evidence),
        }
    return final


def validate_final(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("final payload is not a dict")
    for key in EXPECTED:
        if key not in payload:
            raise ValueError(f"missing key after finalize: {key}")
        entry = payload[key]
        if not isinstance(entry, dict):
            raise ValueError(f"{key} entry is not a dict")
        if set(entry.keys()) != {"answer", "tokens"}:
            raise ValueError(f"{key} must contain only answer and tokens")
        if not isinstance(entry["answer"], list):
            raise ValueError(f"{key}.answer is not a list")
        if not isinstance(entry["tokens"], (int, float)) or entry["tokens"] <= 0:
            raise ValueError(f"{key}.tokens must be a positive number")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: finalize_answers.py <question.txt> <answer.json>", file=sys.stderr)
        return 2

    question_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])

    questions = parse_questions(question_path)
    raw_payload = json.loads(answer_path.read_text(encoding="utf-8"))
    final_payload = finalize_payload(questions, raw_payload)

    answer_path.write_text(
        json.dumps(final_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    reopened = json.loads(answer_path.read_text(encoding="utf-8"))
    validate_final(reopened)
    print(json.dumps(reopened, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
