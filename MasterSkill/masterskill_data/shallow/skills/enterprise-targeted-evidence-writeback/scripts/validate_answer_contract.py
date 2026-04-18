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
