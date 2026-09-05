from verification.software_executor import (
    ControlledSoftwareExecutor,
    ExecutionResult,
)
from verification.software_verification import VerificationStatus
from verification.software_verification_pipeline import (
    SoftwareVerificationPipeline,
)


def make_executor(tmp_path, *, build_code=0, test_code=0):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    return ControlledSoftwareExecutor(
        workspace=workspace,
        test_command=(
            "python",
            "-c",
            f"print('tests'); raise SystemExit({test_code})",
        ),
        build_command=(
            "python",
            "-c",
            f"print('build'); raise SystemExit({build_code})",
        ),
    )


def test_successful_build_and_tests_produce_pass(tmp_path):
    pipeline = SoftwareVerificationPipeline(make_executor(tmp_path))

    result = pipeline.run()

    assert result.status is VerificationStatus.PASS
    assert result.evidence.build.success is True
    assert result.evidence.tests.success is True


def test_failed_build_prevents_tests_from_running(tmp_path):
    pipeline = SoftwareVerificationPipeline(
        make_executor(tmp_path, build_code=1)
    )

    result = pipeline.run()

    assert result.status is VerificationStatus.FAIL
    assert result.evidence.build.success is False
    assert result.evidence.tests.success is False
    assert result.evidence.tests.error == (
        "tests not executed because build failed"
    )


def test_failed_tests_produce_fail(tmp_path):
    pipeline = SoftwareVerificationPipeline(
        make_executor(tmp_path, test_code=1)
    )

    result = pipeline.run()

    assert result.status is VerificationStatus.FAIL
    assert result.evidence.build.success is True
    assert result.evidence.tests.success is False


def test_pipeline_uses_executor_results(tmp_path):
    pipeline = SoftwareVerificationPipeline(make_executor(tmp_path))

    result = pipeline.run()

    assert result.evidence.build.operation == "RUN_BUILD"
    assert result.evidence.tests.operation == "RUN_TESTS"
    assert result.evidence.build.return_code == 0
    assert result.evidence.tests.return_code == 0


class FakeExecutor:
    def __init__(self):
        self.build_called = False
        self.tests_called = False

    def run_build(self):
        self.build_called = True
        return ExecutionResult(
            operation="RUN_BUILD",
            success=True,
            output="verified build",
            return_code=0,
        )

    def run_tests(self):
        self.tests_called = True
        return ExecutionResult(
            operation="RUN_TESTS",
            success=True,
            output="verified tests",
            return_code=0,
        )


def test_pipeline_does_not_accept_agent_supplied_results():
    executor = FakeExecutor()
    pipeline = SoftwareVerificationPipeline(executor)

    result = pipeline.run()

    assert executor.build_called is True
    assert executor.tests_called is True
    assert result.status is VerificationStatus.PASS
    assert result.evidence.build.output == "verified build"
    assert result.evidence.tests.output == "verified tests"
