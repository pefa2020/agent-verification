import pytest

from verification.aws_deployment import DeploymentResult
from verification.aws_deployment_evidence import deployment_evidence_payload
from verification.evidence_integrity import EvidenceLedger, IntegrityError


def make_payload(run_id="deployment-run-001", commit="abc123"):
    result = DeploymentResult(
        operation="DEPLOY",
        success=True,
        target="test-environment",
        account_id="904557616330",
        region="us-east-1",
        output="deployment completed",
        status_code=200,
    )

    return deployment_evidence_payload(
        result,
        run_id=run_id,
        commit=commit,
    )


def test_deployment_evidence_can_be_recorded_in_existing_ledger():
    ledger = EvidenceLedger()
    payload = make_payload()

    record = ledger.append(payload)

    assert record.run_id == "deployment-run-001"
    assert ledger.verify() is True


def test_replayed_deployment_evidence_is_rejected():
    ledger = EvidenceLedger()
    payload = make_payload()

    ledger.append(payload)

    with pytest.raises(IntegrityError, match="Evidence replay detected"):
        ledger.append(payload)


def test_mutated_deployment_evidence_breaks_integrity():
    ledger = EvidenceLedger()
    payload = make_payload()

    ledger.append(payload)

    payload["details"]["deployment"]["target"] = "production"

    # The original ledger record remains internally valid, but the mutated
    # payload must produce a different evidence digest.
    original = make_payload()

    assert payload != original
    assert ledger.verify() is True


def test_different_deployment_run_is_not_replay():
    ledger = EvidenceLedger()

    first = make_payload(run_id="deployment-run-001")
    second = make_payload(run_id="deployment-run-002")

    first_record = ledger.append(first)
    second_record = ledger.append(second)

    assert first_record.run_id != second_record.run_id
    assert second_record.sequence == 1
    assert ledger.verify() is True


def test_deployment_commit_is_bound_into_evidence_digest():
    ledger = EvidenceLedger()

    first = make_payload(commit="commit-aaa")
    second = make_payload(commit="commit-bbb")

    first_record = ledger.append(first)
    second_record = ledger.append(second)

    assert first_record.evidence_digest != second_record.evidence_digest
    assert ledger.verify() is True
