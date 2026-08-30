from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "infra" / "codebuild.yml"
BUILDSPEC = ROOT / "verification" / "aws_buildspec.yml"

def test_cloudformation_template_exists():
    assert TEMPLATE.is_file()

def test_cloudformation_declares_codebuild_project():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "AWS::CodeBuild::Project" in text
    assert "AWS::IAM::Role" in text

def test_codebuild_uses_repository_buildspec():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "BuildSpec: verification/aws_buildspec.yml" in text

def test_codebuild_uses_codeconnections():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "Type: CODECONNECTIONS" in text

def test_buildspec_exists():
    assert BUILDSPEC.is_file()

def test_buildspec_runs_verification():
    text = BUILDSPEC.read_text(encoding="utf-8")
    assert "python -m pytest -q" in text
    assert "python verification/run.py" in text
