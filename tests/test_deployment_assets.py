from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_deploy_scripts_exist():
    assert (ROOT / "infra" / "deploy.sh").is_file()
    assert (ROOT / "infra" / "deploy.ps1").is_file()

def test_run_build_scripts_exist():
    assert (ROOT / "infra" / "run-build.sh").is_file()
    assert (ROOT / "infra" / "run-build.ps1").is_file()

def test_template_grants_codeconnections_access():
    text = (ROOT / "infra" / "codebuild.yml").read_text(encoding="utf-8")
    assert "codeconnections:GetConnectionToken" in text
    assert "codeconnections:GetConnection" in text
    assert "Resource: !Ref CodeConnectionsArn" in text

def test_deploy_script_uses_named_iam_capability():
    text = (ROOT / "infra" / "deploy.sh").read_text(encoding="utf-8")
    assert "--capabilities CAPABILITY_NAMED_IAM" in text
