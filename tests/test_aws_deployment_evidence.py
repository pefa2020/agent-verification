from verification.aws_deployment import DeploymentResult
from verification.aws_deployment_evidence import deployment_evidence_payload


def make_result(*, success=True):
    return DeploymentResult(
        operation="DEPLOY",
        success=success,
        target="test-environment",
        account_id="904557616330",
        region="us-east-1",
        output="deployed successfully" if success else "",
        error="" if success else "deployment failed",
        status_code=200 if success else 500,
    )


def test_successful_deployment_becomes_structured_evidence():
    payload = deployment_evidence_payload(
        make_result(),
        run_id="run-001",
        commit="abc123",
    )

    assert payload["status"] == "PASS"
    assert payload["run_id"] == "run-001"
    assert payload["commit"] == "abc123"

    assert payload["criteria"]["deployment"] == "PASS"
    assert payload["criteria"]["build"] == "BLOCKED"
    assert payload["criteria"]["tests"] == "BLOCKED"
    assert payload["criteria"]["integration"] == "BLOCKED"
    assert payload["criteria"]["smoke"] == "BLOCKED"


def test_failed_deployment_becomes_structured_failure():
    payload = deployment_evidence_payload(
        make_result(success=False),
        run_id="run-002",
        commit="def456",
    )

    assert payload["status"] == "FAIL"
    assert payload["criteria"]["deployment"] == "FAIL"


def test_deployment_identity_is_preserved():
    payload = deployment_evidence_payload(
        make_result(),
        run_id="run-003",
        commit="ghi789",
    )

    deployment = payload["details"]["deployment"]

    assert deployment["operation"] == "DEPLOY"
    assert deployment["target"] == "test-environment"
    assert deployment["account_id"] == "904557616330"
    assert deployment["region"] == "us-east-1"
    assert deployment["status_code"] == 200


def test_deployment_evidence_does_not_claim_full_verification():
    payload = deployment_evidence_payload(
        make_result(),
        run_id="run-004",
        commit="jkl012",
    )

    criteria = payload["criteria"]

    assert criteria["deployment"] == "PASS"
    assert criteria["build"] == "BLOCKED"
    assert criteria["tests"] == "BLOCKED"
    assert criteria["integration"] == "BLOCKED"
    assert criteria["smoke"] == "BLOCKED"
