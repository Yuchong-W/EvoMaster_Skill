"""Local entrypoint for running MasterSkill from the repo checkout.

This avoids ad-hoc sys.path hacks during local debugging when the repo root is
the current working directory.
"""

from pathlib import Path
import sys


def _ensure_repo_parent_on_path() -> None:
    repo_root = Path(__file__).resolve().parent
    repo_parent = repo_root.parent
    repo_parent_str = str(repo_parent)
    if repo_parent_str not in sys.path:
        sys.path.insert(0, repo_parent_str)


def main() -> None:
    _ensure_repo_parent_on_path()
    from MasterSkill.main import main as package_main

    package_main()


if __name__ == "__main__":
    main()
