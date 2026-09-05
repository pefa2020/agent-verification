import pytest

from verification.software_executor import ExecutionResult
from verification.software_verification import VerificationStatus
from verification.software_verification_pipeline import (
    SoftwareVerificationPipeline,
    VerificationPipelineError,
)


class AdversarialExecutor:
    def __init__(self, build_result, test_result=None):
        self.build_result = build_result
        self.test_result = test_result
        self.calls = []

    def run_build(self):
        self.calls.append("build")
        return self.build_result

    def run_tests(self):
        self.calls.append("tests")
        return self.test_result


def test_forged_build_success_cannot_hide_failed_build(tmp_path):
    executor = AdversarialExecutor(
        ExecutionResult(
            operation="RUN_BUILD",
            success=False,
            error="real build failure",
            return_code=1,
        ),
        ExecutionResult(
            operation="RUN_TESTS",
            success=True,
            return_code=0,
        ),
    )

    result = SoftwareVerificationPipeline(executor).run()

    assert result.status is VerificationStatus.FAIL
    assert executor.calls == ["build"]


def test_forged_test_success_cannot_hide_failed_tests(tmp_path):
    executor = AdversarialExecutor(
        ExecutionResult(
            operation="RUN_BUILD",
            success=True,
            return_code=0,
        ),
        ExecutionResult(
            operation="RUN_TESTS",
            success=False,
            error="real test failure",
            return_code=1,
        ),
    )

    result = SoftwareVerificationPipeline(executor).run()

    assert result.status is VerificationStatus.FAIL
    assert executor.calls == ["build", "tests"]


def test_tests_cannot_run_before_build(tmp_path):
    executor = AdversarialExecutor(
        ExecutionResult(
            operation="RUN_BUILD",
            success=False,
            error="build blocked",
            return_code=1,
        ),
        ExecutionResult(
            operation="RUN_TESTS",
            success=True,
            return_code=0,
        ),
    )

    SoftwareVerificationPipeline(executor).run()

    assert executor.calls == ["build"]


def test_invalid_build_result_is_rejected(tmp_path):
    executor = AdversarialExecutor(
        build_result={"success": True},
        test_result=None,
    )

    with pytest.raises(VerificationPipelineError):
        SoftwareVerificationPipeline(executor).run()


def test_invalid_test_result_is_rejected(tmp_path):
    executor = AdversarialExecutor(
        build_result=ExecutionResult(
            operation="RUN_BUILD",
            success=True,
            return_code=0,
        ),
        test_result={"success": True},
    )

    with pytest.raises(VerificationPipelineError):
        SoftwareVerificationPipeline(executor).run()


def test_wrong_build_operation_cannot_become_success(tmp_path):
    executor = AdversarialExecutor(
        build_result=ExecutionResult(
            operation="RUN_TESTS",
            success=True,
            return_code=0,
        ),
        test_result=None,
    )

    with pytest.raises(Exception):
        SoftwareVerificationPipeline(executor).run()


def test_wrong_test_operation_cannot_become_success(tmp_path):
    executor = AdversarialExecutor(
        build_result=ExecutionResult(
            operation="RUN_BUILD",
            success=True,
            return_code=0,
        ),
        test_result=ExecutionResult(
            operation="RUN_BUILD",
            success=True,
            return_code=0,
        ),
    )

    with pytest.raises(Exception):
        SoftwareVerificationPipeline(executor).run()
