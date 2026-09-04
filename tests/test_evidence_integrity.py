import pytest

from verification.evidence_integrity import EvidenceLedger, IntegrityError, canonicalize, evidence_digest


def evidence(run_id="run-1", status="PASS"):
    return {
        "schema_version": "1.0",
        "status": status,
        "run_id": run_id,
        "commit": "abc123",
        "criteria": {"build": "PASS", "tests": "PASS", "integration": "PASS", "smoke": "PASS"},
    }


def test_canonicalization_is_order_independent():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert canonicalize(left) == canonicalize(right)
    assert evidence_digest(left) == evidence_digest(right)


def test_same_evidence_cannot_be_replayed():
    ledger = EvidenceLedger()
    payload = evidence()
    ledger.append(payload)
    with pytest.raises(IntegrityError, match="replay"):
        ledger.append(payload)


def test_different_runs_do_not_share_replay_identity():
    ledger = EvidenceLedger()
    ledger.append(evidence(run_id="run-1"))
    ledger.append(evidence(run_id="run-2"))
    assert len(ledger.records) == 2
    assert ledger.verify()


def test_mutated_payload_produces_different_digest():
    original = evidence()
    mutated = dict(original)
    mutated["commit"] = "tampered"
    assert evidence_digest(original) != evidence_digest(mutated)


def test_run_id_is_required_for_ledger_binding():
    ledger = EvidenceLedger()
    payload = evidence()
    del payload["run_id"]
    with pytest.raises(IntegrityError, match="run_id"):
        ledger.append(payload)


def test_history_is_chained():
    ledger = EvidenceLedger()
    first = ledger.append(evidence(run_id="run-1"))
    second = ledger.append(evidence(run_id="run-2"))
    assert second.previous_digest == first.record_digest
    assert ledger.verify()


def test_tampered_history_is_detected():
    ledger = EvidenceLedger()
    ledger.append(evidence(run_id="run-1"))
    ledger.append(evidence(run_id="run-2"))
    records = list(ledger.records)
    records[0] = records[0].__class__(
        records[0].run_id,
        records[0].sequence,
        "f" * 64,
        records[0].previous_digest,
        records[0].record_digest,
    )
    ledger._records = records
    assert not ledger.verify()


def test_out_of_order_history_is_detected():
    ledger = EvidenceLedger()
    ledger.append(evidence(run_id="run-1"))
    ledger.append(evidence(run_id="run-2"))
    records = list(ledger.records)
    records.reverse()
    ledger._records = records
    assert not ledger.verify()


def test_duplicate_sequence_is_detected():
    ledger = EvidenceLedger()
    ledger.append(evidence(run_id="run-1"))
    ledger.append(evidence(run_id="run-2"))
    records = list(ledger.records)
    records[1] = records[1].__class__(
        records[1].run_id,
        records[0].sequence,
        records[1].evidence_digest,
        records[1].previous_digest,
        records[1].record_digest,
    )
    ledger._records = records
    assert not ledger.verify()


def test_empty_history_is_valid():
    assert EvidenceLedger().verify()
