import pytest

from verification.software_executor import (
    ControlledSoftwareExecutor,
    ExecutorError,
)


def make_executor(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    protected = tmp_path / "protected"
    protected.mkdir()
    (protected / "secret.txt").write_text("protected")

    return ControlledSoftwareExecutor(
        workspace=workspace,
        protected_paths=(protected,),
        test_command=("python", "-c", "print('tests pass')"),
        build_command=("python", "-c", "print('build pass')"),
    ), workspace, protected


def test_parent_traversal_is_rejected(tmp_path):
    executor, _, _ = make_executor(tmp_path)

    with pytest.raises(ExecutorError):
        executor.create_file("../escape.txt", "blocked")


def test_nested_parent_traversal_is_rejected(tmp_path):
    executor, _, _ = make_executor(tmp_path)

    with pytest.raises(ExecutorError):
        executor.create_file("a/../../escape.txt", "blocked")


def test_absolute_path_outside_workspace_is_rejected(tmp_path):
    executor, _, _ = make_executor(tmp_path)

    outside = tmp_path / "outside.txt"

    with pytest.raises(ExecutorError):
        executor.create_file(str(outside), "blocked")

    assert not outside.exists()


def test_protected_resource_is_rejected(tmp_path):
    executor, _, protected = make_executor(tmp_path)

    with pytest.raises(ExecutorError):
        executor.read_file(str(protected / "secret.txt"))


def test_arbitrary_shell_is_not_available(tmp_path):
    executor, _, _ = make_executor(tmp_path)

    assert not hasattr(executor, "run_shell")


def test_build_command_cannot_be_replaced_by_request(tmp_path):
    executor, _, _ = make_executor(tmp_path)

    with pytest.raises(TypeError):
        executor.run_build(command=("python", "-c", "print('unauthorized')"))


def test_test_command_cannot_be_replaced_by_request(tmp_path):
    executor, _, _ = make_executor(tmp_path)

    with pytest.raises(TypeError):
        executor.run_tests(command=("python", "-c", "print('unauthorized')"))


def test_workspace_symlink_escape_is_rejected(tmp_path):
    executor, workspace, protected = make_executor(tmp_path)

    link = workspace / "escape"

    try:
        link.symlink_to(protected, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")

    with pytest.raises(ExecutorError):
        executor.read_file("escape/secret.txt")


def test_missing_file_failure_is_explicit(tmp_path):
    executor, _, _ = make_executor(tmp_path)

    result = executor.read_file("missing.txt")

    assert result.success is False
    assert result.operation == "READ_FILE"
    assert result.target == "missing.txt"
    assert result.error
