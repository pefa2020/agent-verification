"""Verifier-owned build/test verification pipeline for v3.2."""

from __future__ import annotations

from dataclasses import dataclass

from verification.software_executor import (
    ControlledSoftwareExecutor,
    ExecutionResult,
)
from verification.software_verification import (
    VerificationEvidence,
    VerificationStatus,
    create_evidence,
)


class VerificationPipelineError(RuntimeError):
    """Raised when the verification pipeline cannot execute safely."""


@dataclass(frozen=True)
class PipelineResult:
    evidence: VerificationEvidence
    status: VerificationStatus


class SoftwareVerificationPipeline:
    """Runs the verifier-controlled build/test sequence."""

    def __init__(self, executor: ControlledSoftwareExecutor) -> None:
        self.executor = executor

    def run(self) -> PipelineResult:
        build = self.executor.run_build()

        if not isinstance(build, ExecutionResult):
            raise VerificationPipelineError(
                "executor returned an invalid build result"
            )

        if not build.success:
            evidence = create_evidence(
                build,
                ExecutionResult(
                    operation="RUN_TESTS",
                    success=False,
                    error="tests not executed because build failed",
                ),
            )
            return PipelineResult(evidence, evidence.status)

        tests = self.executor.run_tests()

        if not isinstance(tests, ExecutionResult):
            raise VerificationPipelineError(
                "executor returned an invalid test result"
            )

        evidence = create_evidence(build, tests)

        return PipelineResult(evidence, evidence.status)
