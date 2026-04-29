import hashlib
import json
import os
import sys


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 finalize_tpp_outputs.py /app/problem.json", file=sys.stderr)
        return 2

    manifest_path = sys.argv[1]
    manifest = _read_json(manifest_path)

    if not isinstance(manifest, list):
        print(f"ERROR: {manifest_path} must be a JSON array", file=sys.stderr)
        return 2

    failures = 0
    rows = []

    for i, entry in enumerate(manifest):
        if not isinstance(entry, dict):
            print(f"ERROR: entry[{i}] must be an object", file=sys.stderr)
            failures += 1
            continue

        plan_path = entry.get("plan_output")
        if not isinstance(plan_path, str) or not plan_path:
            print(f"ERROR: entry[{i}].plan_output missing/invalid", file=sys.stderr)
            failures += 1
            continue

        if not os.path.exists(plan_path):
            print(f"ERROR: missing plan_output: {plan_path}", file=sys.stderr)
            failures += 1
            continue

        try:
            with open(plan_path, "rb") as f:
                data = f.read()
        except Exception as e:
            print(f"ERROR: cannot read {plan_path}: {e}", file=sys.stderr)
            failures += 1
            continue

        size = len(data)
        if size == 0:
            print(f"ERROR: empty plan_output: {plan_path}", file=sys.stderr)
            failures += 1
            continue

        ends_with_newline = data.endswith(b"\n")
        text = None
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            print(f"ERROR: non-utf8 plan_output: {plan_path}", file=sys.stderr)
            failures += 1
            continue

        lines = [ln for ln in text.splitlines() if ln.strip() != ""]
        if not lines:
            print(f"ERROR: no non-empty action lines in: {plan_path}", file=sys.stderr)
            failures += 1
            continue

        bad_lines = 0
        for ln in lines:
            s = ln.strip()
            if any(s.startswith(prefix) for prefix in (";", "#", "//")):
                bad_lines += 1
            if s[0].isdigit() and ":" in s[:6]:
                bad_lines += 1

        if bad_lines:
            print(f"ERROR: suspicious/comment/numbered lines in: {plan_path}", file=sys.stderr)
            failures += 1

        rows.append(
            {
                "idx": i,
                "plan_output": plan_path,
                "bytes": size,
                "lines": len(lines),
                "ends_with_newline": bool(ends_with_newline),
                "sha256": _sha256_bytes(data),
            }
        )

    print(json.dumps({"manifest": manifest_path, "outputs": rows, "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
