import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: strict_plan_lint.py <plan.txt>")
        return 2

    plan_path = Path(sys.argv[1])
    if not plan_path.exists():
        print(f"missing plan file: {plan_path}")
        return 1

    lines = [line.rstrip("\n") for line in plan_path.read_text(encoding="utf-8").splitlines()]
    if not lines:
        print("empty plan file")
        return 1

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            print(f"empty line at {index}")
            return 1
        if stripped.count("(") != 1 or stripped.count(")") != 1:
            print(f"malformed action at line {index}: {stripped}")
            return 1
        if "(" not in stripped or ")" not in stripped:
            print(f"missing parens at line {index}: {stripped}")
            return 1

    print("plan lint OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
