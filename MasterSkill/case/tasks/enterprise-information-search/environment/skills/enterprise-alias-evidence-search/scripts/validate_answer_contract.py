import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_answer_contract.py <answer.json>")
        return 2

    answer_path = Path(sys.argv[1])
    if not answer_path.exists():
        print(f"missing file: {answer_path}")
        return 1

    payload = json.loads(answer_path.read_text(encoding="utf-8"))
    expected = ("q1", "q2", "q3")

    if not isinstance(payload, dict):
        print("answer payload is not a dict")
        return 1

    for key in expected:
        if key not in payload:
            print(f"missing key: {key}")
            return 1
        entry = payload[key]
        if not isinstance(entry, dict):
            print(f"{key} entry is not a dict")
            return 1
        if "answer" not in entry or "tokens" not in entry:
            print(f"{key} missing answer or tokens")
            return 1
        if not isinstance(entry["answer"], list):
            print(f"{key}.answer is not a list")
            return 1
        tokens = entry["tokens"]
        if not isinstance(tokens, (int, float)):
            print(f"{key}.tokens is not numeric")
            return 1
        if tokens <= 0:
            print(f"{key}.tokens must be positive")
            return 1

    print("answer contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
