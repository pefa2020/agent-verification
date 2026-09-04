"""Integrity, replay, and tamper-evident history primitives for verification evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


class IntegrityError(ValueError):
    """Raised when evidence or history integrity validation fails."""


def canonicalize(payload: dict[str, Any]) -> bytes:
    """Return a deterministic UTF-8 representation of a JSON object."""
    if not isinstance(payload, dict):
        raise IntegrityError("Evidence must be a JSON object")
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IntegrityError("Evidence is not canonically serializable") from exc


def evidence_digest(payload: dict[str, Any]) -> str:
    """Compute a SHA-256 digest over canonical evidence."""
    return hashlib.sha256(canonicalize(payload)).hexdigest()


@dataclass(frozen=True)
class EvidenceRecord:
    run_id: str
    sequence: int
    evidence_digest: str
    previous_digest: str
    record_digest: str


class EvidenceLedger:
    """In-memory append-only ledger enforcing run binding and replay resistance."""

    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []
        self._accepted: set[tuple[str, str]] = set()

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records)

    def append(self, payload: dict[str, Any]) -> EvidenceRecord:
        if not isinstance(payload, dict):
            raise IntegrityError("Evidence must be a JSON object")
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            raise IntegrityError("run_id must be a non-empty string")

        digest = evidence_digest(payload)
        key = (run_id, digest)
        if key in self._accepted:
            raise IntegrityError("Evidence replay detected")

        sequence = len(self._records)
        previous = self._records[-1].record_digest if self._records else "0" * 64
        material = f"{run_id}\n{sequence}\n{digest}\n{previous}".encode("utf-8")
        record_digest = hashlib.sha256(material).hexdigest()
        record = EvidenceRecord(run_id, sequence, digest, previous, record_digest)
        self._records.append(record)
        self._accepted.add(key)
        return record

    def verify(self) -> bool:
        previous = "0" * 64
        accepted: set[tuple[str, str]] = set()
        for expected_sequence, record in enumerate(self._records):
            if record.sequence != expected_sequence:
                return False
            key = (record.run_id, record.evidence_digest)
            if key in accepted:
                return False
            material = f"{record.run_id}\n{record.sequence}\n{record.evidence_digest}\n{previous}".encode("utf-8")
            if hashlib.sha256(material).hexdigest() != record.record_digest:
                return False
            accepted.add(key)
            previous = record.record_digest
        return True
