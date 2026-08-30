import json
import os
import subprocess
import sys
from pathlib import Path

def main():
    run_id = os.getenv("GITHUB_RUN_ID", "LOCAL")
    commit = os.getenv("GITHUB_SHA", "LOCAL")

    command = [sys.executable, "-m", "pytest", "-q"]
    completed = subprocess.run(command, cwd=Path.cwd())

    status = "PASS" if completed.returncode == 0 else "FAIL"

    result = {
        "status": status,
        "run_id": run_id,
        "commit": commit,
        "details": {
            "command": "python -m pytest -q",
            "return_code": completed.returncode,
        },
    }

    output = Path("verification-result.json")
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # GitHub Actions can consume this as a step output through GITHUB_OUTPUT.
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"verification_status={status}\n")

    return completed.returncode

if __name__ == "__main__":
    raise SystemExit(main())
