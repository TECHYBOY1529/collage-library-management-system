"""
Safe Automated Daily Git Commit & Push Script (Phase 13)
-------------------------------------------------------
Checks eligible project files, runs pytest verification, and pushes verified
commits to the configured GitHub remote and branch without ever force-pushing
or staging secrets/databases.
"""

import os
import subprocess
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ALLOWED_PATHS = [
    "app",
    "tests",
    "docs",
    "scripts",
    "config.py",
    "run.py",
    "seed.py",
    "requirements.txt",
    ".gitignore",
    ".env.example",
    "README.md",
]

FORBIDDEN_PATTERNS = (
    ".env",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pem",
    ".key",
    "instance/",
    "__pycache__",
)


def run_cmd(args: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def main() -> int:
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    print(f"=== [Daily Git Sync] Started at {timestamp} ===")

    # 1. Verify Git repository and active branch
    branch_res = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch_res.returncode != 0:
        print("[ERROR] Current directory is not a valid Git repository.")
        return 1
    current_branch = branch_res.stdout.strip()
    print(f"[INFO] Active Branch: {current_branch}")

    # 2. Inspect status for eligible changes
    status_res = run_cmd(["git", "status", "--porcelain"])
    if status_res.returncode != 0:
        print(f"[ERROR] Failed to inspect git status: {status_res.stderr}")
        return 1

    lines = [line.strip() for line in status_res.stdout.splitlines() if line.strip()]
    if not lines:
        print("[INFO] Working tree is clean. No eligible changes to commit. Exiting without empty commit.")
        return 0

    # Filter out any forbidden files
    eligible_stage_targets = []
    for rel_path in ALLOWED_PATHS:
        full_p = os.path.join(PROJECT_ROOT, rel_path)
        if os.path.exists(full_p):
            eligible_stage_targets.append(rel_path)

    # 3. Run automated pytest suite before staging/committing
    pytest_bin = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "pytest.exe")
    if not os.path.exists(pytest_bin):
        pytest_bin = "pytest"

    print("[INFO] Running automated pytest verification suite...")
    test_res = run_cmd([pytest_bin, "-q"])
    if test_res.returncode != 0:
        print("[ERROR] Automated tests failed! Aborting commit and push to protect remote branch.")
        print(test_res.stdout)
        print(test_res.stderr)
        return 2
    print("[PASS] Pytest verification passed.")

    # 4. Stage only intended project paths
    run_cmd(["git", "add", "--"] + eligible_stage_targets)

    # Safety check staged files for any forbidden secret/db patterns
    staged_res = run_cmd(["git", "diff", "--cached", "--name-only"])
    staged_files = [f.strip() for f in staged_res.stdout.splitlines() if f.strip()]
    for sf in staged_files:
        if sf == ".env" or any(sf.endswith(pat) for pat in (".db", ".sqlite", ".sqlite3", ".pem", ".key")):
            run_cmd(["git", "reset", "HEAD", "--", sf])
            print(f"[SECURITY] Unstaged forbidden file: {sf}")

    staged_res = run_cmd(["git", "diff", "--cached", "--name-only"])
    staged_files = [f.strip() for f in staged_res.stdout.splitlines() if f.strip()]
    if not staged_files:
        print("[INFO] No eligible project files changed after filtering. Exiting cleanly.")
        return 0

    # 5. Create descriptive commit
    commit_msg = f"chore(daily-sync): automated verified project update ({datetime.now().strftime('%Y-%m-%d')})"
    commit_res = run_cmd(["git", "commit", "-m", commit_msg])
    if commit_res.returncode != 0:
        print(f"[ERROR] Commit failed: {commit_res.stderr}")
        return 3

    hash_res = run_cmd(["git", "rev-parse", "--short", "HEAD"])
    commit_hash = hash_res.stdout.strip()
    print(f"[INFO] Created commit {commit_hash}: {commit_msg}")

    # 6. Check configured remote and push safely (never force-push)
    remote_res = run_cmd(["git", "remote", "get-url", "origin"])
    if remote_res.returncode != 0:
        print("[WARN] No 'origin' remote configured yet. Local commit succeeded; skipping remote push.")
        return 0

    remote_url = remote_res.stdout.strip()
    push_res = run_cmd(["git", "push", "origin", current_branch])
    if push_res.returncode != 0:
        print(f"[ERROR] Push to {remote_url} ({current_branch}) failed:\n{push_res.stderr}")
        return 4

    print(f"[SUCCESS] Verified push to {remote_url} (branch: {current_branch}, commit: {commit_hash}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
