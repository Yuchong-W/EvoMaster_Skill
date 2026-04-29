# TPP PDDL Batch Solve+Verify (Minimal)

Solves `pddl-tpp-planning` batches by running the packaged pyperplan batch solver on `/app/problem.json`, then immediately verifies every emitted `plan_output` (and required sibling sidecar artifacts) with the bundled checkers; includes a tiny finalization script to sanity-check outputs and detect truncation.

## When to Use

Use when the task is `pddl-tpp-planning` (Travelling Purchase Problem) and `/app/problem.json` is a JSON array of entries with `domain`, `problem`, and `plan_output` paths that must be written exactly as specified.

## How to Use

1) Treat `/app/problem.json` as the sole manifest; do not open domain/problem PDDL unless a checker error forces it.

2) Solve the full batch in one call:
   `python3 /root/.codex/skills/pddl-tpp-pyperplan-batch/solve_tpp_batch.py /app/problem.json`

3) Verify with the task checker (must pass):
   `python3 /root/.codex/skills/pddl-tpp-plan-emitter/scripts/check_tpp_outputs.py /app/problem.json`

4) If verification fails:
   - Run strict lint to pinpoint formatting issues:
     `python3 /root/.codex/skills/pddl-tpp-plan-emitter/scripts/strict_plan_lint.py /app/problem.json`
   - Fix only the blocking issue (typically empty/truncated plan file, wrong action/object tokenization, missing sidecar), then rerun steps (2) and (3). Avoid manual plan authoring unless the solver cannot produce a plan.

5) Finalization checklist (must do before exiting):
   - Confirm every `plan_output` path from `/app/problem.json` exists and is non-empty.
   - Reopen each `plan_output` and ensure it is plain text with exactly one action per line (no numbering), and ends with a newline.
   - Confirm required sibling sidecar artifacts (if expected by the checker) exist next to each `plan_output`.
   - Run the output sanity script (prints a deterministic summary for downstream auditing):
     `python3 finalize_tpp_outputs.py /app/problem.json`

## Scripts

### finalize_tpp_outputs.py

```
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

```

