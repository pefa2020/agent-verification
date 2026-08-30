from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_preflight_scripts_exist():
    assert (ROOT / "infra" / "preflight.sh").is_file()
    assert (ROOT / "infra" / "preflight.ps1").is_file()

def test_preflight_checks_identity_and_connection():
    bash = (ROOT / "infra" / "preflight.sh").read_text(encoding="utf-8")
    assert "aws sts get-caller-identity" in bash
    assert "aws codeconnections get-connection" in bash
    assert "CODECONNECTIONS_ARN" in bash
