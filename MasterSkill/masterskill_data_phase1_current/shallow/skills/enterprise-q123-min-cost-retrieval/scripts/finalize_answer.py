import json
import math
import re
import sys
from pathlib import Path

QUESTION_RE = re.compile(r'"(q[123])"\s*:\s*(.+?)(?:,)?$')


def parse_questions(question_path: Path) -> dict[str, str]:
    questions: dict[str, str] = {}
    for raw_line in question_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        match = QUESTION_RE.search(line)
        if not match:
            continue
        key, text = match.groups()
        questions[key] = text.strip().rstrip(",")
    return questions


def estimate_tokens(question_text: str, answers: list[str]) -> int:
    # Deterministic numeric estimate derived from the *actual* Q/A text.
    # Produces per-question variation without relying on runtime token counters.
    blob = question_text + "\n" + json.dumps(answers, ensure_ascii=False, separators=(",", ":"))
    chars = len(blob)
    # ~4 chars/token heuristic + fixed overhead; keep comfortably >0.
    return max(256, int(math.ceil(chars / 4.0)) + 128)


def validate_contract(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("answer payload is not a dict")

    for key in ("q1", "q2", "q3"):
        if key not in payload:
            raise ValueError(f"missing key: {key}")
        entry = payload[key]
        if not isinstance(entry, dict):
            raise ValueError(f"{key} entry is not a dict")
        if "answer" not in entry:
            raise ValueError(f"{key} missing answer")
        if "tokens" not in entry:
            raise ValueError(f"{key} missing tokens")
        ans = entry["answer"]
        if not isinstance(ans, list):
            raise ValueError(f"{key}.answer is not a list")
        if not all(isinstance(x, str) for x in ans):
            raise ValueError(f"{key}.answer must be list[str]")
        tok = entry["tokens"]
        if not isinstance(tok, (int, float)):
            raise ValueError(f"{key}.tokens is not numeric")
        if tok <= 0:
            raise ValueError(f"{key}.tokens must be positive")

    return payload


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: finalize_answer.py <question.txt> <answer.json>")
        return 2

    question_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])

    questions = parse_questions(question_path)
    payload = json.loads(answer_path.read_text(encoding="utf-8"))

    # Normalize answers to list even if someone wrote a scalar.
    for key in ("q1", "q2", "q3"):
        entry = payload.get(key)
        if not isinstance(entry, dict):
            raise ValueError(f"{key} entry is not a dict")
        ans = entry.get("answer")
        if isinstance(ans, str):
            entry["answer"] = [ans]
        elif ans is None:
            entry["answer"] = []
        elif not isinstance(ans, list):
            entry["answer"] = [str(ans)]

    # Set deterministic token estimates from actual Q/A text.
    for key in ("q1", "q2", "q3"):
        qtext = questions.get(key, "")
        answers = payload[key]["answer"]
        payload[key]["tokens"] = estimate_tokens(qtext, answers)

    validate_contract(payload)

    answer_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("finalized /root/answer.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
