import json
import math
import re
import sys
from pathlib import Path

QUESTION_RE = re.compile(r'"(q[123])"\s*:\s*(.+?)(?:,)?$')
EXPECTED = ("q1", "q2", "q3")


def parse_questions(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            out = {}
            for key in EXPECTED:
                value = data.get(key)
                if isinstance(value, str):
                    out[key] = value
            if out:
                return out
    except Exception:
        pass

    questions = {}
    for raw_line in text.splitlines():
        match = QUESTION_RE.search(raw_line.strip())
        if match:
            key, value = match.groups()
            questions[key] = value.strip().rstrip(",")
    return questions


def normalize_str_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def estimate_tokens(question_text: str, answers: list[str], evidence: list[str]) -> int:
    blob = question_text + "\n" + json.dumps(answers, ensure_ascii=False) + "\n" + json.dumps(evidence, ensure_ascii=False)
    chars = len(blob)
    return max(48, int(math.ceil(chars / 4.0)) + 16 * max(1, len(answers)) + 8 * len(evidence))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: finalize_enterprise_answer.py <question.txt> <answer.json>")
        return 2

    question_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])

    questions = parse_questions(question_path)
    payload = json.loads(answer_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("answer payload is not a dict")

    for key in EXPECTED:
        if key not in payload or not isinstance(payload[key], dict):
            raise ValueError(f"missing or invalid entry: {key}")
        entry = payload[key]
        answers = entry.get("answer")
        if not isinstance(answers, list):
            raise ValueError(f"{key}.answer must be a list")
        answers = [str(item) for item in answers]
        evidence = normalize_str_list(entry.pop("_evidence", []))
        entry["answer"] = answers
        entry["tokens"] = estimate_tokens(questions.get(key, ""), answers, evidence)

    for key in EXPECTED:
        entry = payload[key]
        if not isinstance(entry.get("tokens"), (int, float)) or entry["tokens"] <= 0:
            raise ValueError(f"{key}.tokens must be numeric and positive")
        unknown = set(entry.keys()) - {"answer", "tokens"}
        if unknown:
            raise ValueError(f"{key} has unexpected fields: {sorted(unknown)}")

    answer_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(answer_path.read_text(encoding="utf-8"))
    print("answer finalized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
