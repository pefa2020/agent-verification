from pathlib import Path
import sys

import pytest

from verification.software_executor import ControlledSoftwareExecutor, ExecutorError


@pytest.fixture
def executor(tmp_path: Path):
    return ControlledSoftwareExecutor(
        tmp_path,
        test_command=(sys.executable, "-c", "print('tests-pass')"),
        build_command=(sys.executable, "-c", "print('build-pass')"),
    )


def test_create_read_write_delete_lifecycle(executor):
    created = executor.execute("CREATE_FILE", path="src/app.py", content="print('v1')\n")
    assert created.success
    assert executor.execute("READ_FILE", path="src/app.py").output == "print('v1')\n"
    updated = executor.execute("WRITE_FILE", path="src/app.py", content="print('v2')\n")
    assert updated.success
    assert executor.execute("READ_FILE", path="src/app.py").output == "print('v2')\n"
    assert executor.execute("DELETE_FILE", path="src/app.py").success


def test_write_requires_existing_file(executor):
    with pytest.raises(ExecutorError, match="existing file"):
        executor.execute("WRITE_FILE", path="new.py", content="x")


def test_create_rejects_existing_file(executor):
    executor.execute("CREATE_FILE", path="app.py", content="x")
    with pytest.raises(ExecutorError, match="already exists"):
        executor.execute("CREATE_FILE", path="app.py", content="y")


@pytest.mark.parametrize("path", ["../outside.txt", "../../outside.txt", "../v3.1_SPEC.md"])
def test_path_traversal_is_rejected(executor, path):
    with pytest.raises(ExecutorError, match="escapes the workspace"):
        executor.execute("CREATE_FILE", path=path, content="blocked")


def test_absolute_path_is_rejected(executor, tmp_path):
    with pytest.raises(ExecutorError, match="absolute paths"):
        executor.execute("CREATE_FILE", path=str(tmp_path / "escape.txt"), content="blocked")


def test_protected_resources_are_not_mutable(executor):
    with pytest.raises(ExecutorError, match="protected resource"):
        executor.execute("CREATE_FILE", path="verification/new.py", content="blocked")
    executor.execute("CREATE_FILE", path="app.py", content="safe")
    with pytest.raises(ExecutorError, match="protected resource"):
        executor.execute("WRITE_FILE", path="app.py/../verification/new.py", content="blocked")


def test_unknown_operation_is_rejected(executor):
    with pytest.raises(ExecutorError, match="unknown operation"):
        executor.execute("RUN_SHELL", command="echo unsafe")


def test_arbitrary_shell_is_not_exposed(executor):
    assert "RUN_SHELL" not in executor.OPERATIONS
    with pytest.raises(ExecutorError):
        executor.execute("RUN_SHELL", command="echo unsafe")


def test_build_uses_fixed_configured_command(executor):
    result = executor.execute("RUN_BUILD")
    assert result.success
    assert result.return_code == 0
    assert "build-pass" in result.output


def test_tests_use_fixed_configured_command(executor):
    result = executor.execute("RUN_TESTS")
    assert result.success
    assert result.return_code == 0
    assert "tests-pass" in result.output


def test_command_failure_is_explicit(tmp_path):
    executor = ControlledSoftwareExecutor(
        tmp_path,
        test_command=(sys.executable, "-c", "raise SystemExit(3)"),
        build_command=(sys.executable, "-c", "raise SystemExit(2)"),
    )
    result = executor.execute("RUN_TESTS")
    assert result.success is False
    assert result.return_code == 3
    assert "code 3" in result.error


def test_malformed_arguments_are_rejected(executor):
    with pytest.raises(ExecutorError, match="path"):
        executor.execute("READ_FILE", path=None)
    with pytest.raises(ExecutorError, match="string path and content"):
        executor.execute("CREATE_FILE", path="x.txt", content=123)


def test_repeated_operations_are_deterministic(executor):
    executor.execute("CREATE_FILE", path="a.txt", content="same")
    first = executor.execute("READ_FILE", path="a.txt")
    second = executor.execute("READ_FILE", path="a.txt")
    assert first == second
