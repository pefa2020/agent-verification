"""Verifier-owned filesystem and configured-command executor for v3.1."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import Sequence


class ExecutorError(RuntimeError):
    """Raised when a requested software operation violates the executor boundary."""


@dataclass(frozen=True)
class ExecutionResult:
    operation: str
    success: bool
    target: str = ""
    output: str = ""
    error: str = ""
    return_code: int | None = None


class ControlledSoftwareExecutor:
    """Constrained software executor for a verifier-authorized workspace.

    This class deliberately contains no arbitrary shell interface. File operations
    are canonicalized against the workspace root, and build/test commands must be
    supplied as fixed argument sequences by the verifier.
    """

    OPERATIONS = frozenset(
        {"READ_FILE", "WRITE_FILE", "CREATE_FILE", "DELETE_FILE", "RUN_TESTS", "RUN_BUILD"}
    )

    def __init__(
        self,
        workspace: str | os.PathLike[str],
        *,
        test_command: Sequence[str],
        build_command: Sequence[str],
        protected_paths: Sequence[str] = ("dfa", "verification", ".github", "V3.1_SPEC.md"),
        timeout_seconds: float = 120.0,
    ) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.test_command = self._validate_command(test_command, "test_command")
        self.build_command = self._validate_command(build_command, "build_command")
        self.protected_paths = tuple(protected_paths)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    @staticmethod
    def _validate_command(command: Sequence[str], name: str) -> tuple[str, ...]:
        if isinstance(command, (str, bytes)) or not command:
            raise ValueError(f"{name} must be a non-empty argument sequence")
        values = tuple(str(part) for part in command)
        if any(not part for part in values):
            raise ValueError(f"{name} cannot contain empty arguments")
        return values

    def _path(self, value: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ExecutorError("path must be a non-empty string")
        candidate = Path(value)
        if candidate.is_absolute():
            raise ExecutorError("absolute paths are not permitted")
        resolved = (self.workspace / candidate).resolve()
        try:
            resolved.relative_to(self.workspace)
        except ValueError as exc:
            raise ExecutorError("path escapes the workspace") from exc
        return resolved

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.workspace).as_posix()

    def _protected(self, path: Path) -> bool:
        relative = Path(self._relative(path))
        return any(
            relative == Path(protected) or Path(protected) in relative.parents
            for protected in self.protected_paths
        )

    def _guard_mutation(self, path: Path) -> None:
        if self._protected(path):
            raise ExecutorError(f"protected resource: {self._relative(path)}")

    def execute(self, operation: str, **arguments: object) -> ExecutionResult:
        """Execute exactly one supported operation.

        Authorization/state gating is intentionally owned by AgentToolRuntime;
        this executor enforces the resource and process boundary after a request
        has been authorized and routed here.
        """
        if operation not in self.OPERATIONS:
            raise ExecutorError(f"unknown operation: {operation}")
        if operation == "READ_FILE":
            return self.read_file(arguments.get("path"))
        if operation == "WRITE_FILE":
            return self.write_file(arguments.get("path"), arguments.get("content"))
        if operation == "CREATE_FILE":
            return self.create_file(arguments.get("path"), arguments.get("content"))
        if operation == "DELETE_FILE":
            return self.delete_file(arguments.get("path"))
        if operation == "RUN_TESTS":
            return self.run_tests()
        return self.run_build()

    def read_file(self, path: object) -> ExecutionResult:
        target = self._path(path) if isinstance(path, str) else None
        if target is None:
            raise ExecutorError("path must be a non-empty string")
        if target.is_dir():
            raise ExecutorError("cannot read a directory")
        try:
            output = target.read_text(encoding="utf-8")
        except OSError as exc:
            return ExecutionResult("READ_FILE", False, self._relative(target), error=str(exc))
        return ExecutionResult("READ_FILE", True, self._relative(target), output=output)

    def write_file(self, path: object, content: object) -> ExecutionResult:
        if not isinstance(path, str) or not isinstance(content, str):
            raise ExecutorError("WRITE_FILE requires string path and content")
        target = self._path(path)
        self._guard_mutation(target)
        if not target.exists() or target.is_dir():
            raise ExecutorError("WRITE_FILE requires an existing file")
        try:
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ExecutionResult("WRITE_FILE", False, self._relative(target), error=str(exc))
        return ExecutionResult("WRITE_FILE", True, self._relative(target))

    def create_file(self, path: object, content: object) -> ExecutionResult:
        if not isinstance(path, str) or not isinstance(content, str):
            raise ExecutorError("CREATE_FILE requires string path and content")
        target = self._path(path)
        self._guard_mutation(target)
        if target.exists():
            raise ExecutorError("CREATE_FILE target already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ExecutionResult("CREATE_FILE", False, self._relative(target), error=str(exc))
        return ExecutionResult("CREATE_FILE", True, self._relative(target))

    def delete_file(self, path: object) -> ExecutionResult:
        if not isinstance(path, str):
            raise ExecutorError("DELETE_FILE requires a string path")
        target = self._path(path)
        self._guard_mutation(target)
        if not target.exists() or not target.is_file():
            raise ExecutorError("DELETE_FILE target does not exist as a file")
        try:
            target.unlink()
        except OSError as exc:
            return ExecutionResult("DELETE_FILE", False, self._relative(target), error=str(exc))
        return ExecutionResult("DELETE_FILE", True, self._relative(target))

    def run_tests(self) -> ExecutionResult:
        return self._run("RUN_TESTS", self.test_command)

    def run_build(self) -> ExecutionResult:
        return self._run("RUN_BUILD", self.build_command)

    def _run(self, operation: str, command: tuple[str, ...]) -> ExecutionResult:
        try:
            completed = subprocess.run(
                command,
                cwd=self.workspace,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return ExecutionResult(operation, False, output="", error=str(exc))
        output = (completed.stdout or "") + (completed.stderr or "")
        return ExecutionResult(
            operation,
            completed.returncode == 0,
            target=" ".join(command),
            output=output,
            error="" if completed.returncode == 0 else f"command exited with code {completed.returncode}",
            return_code=completed.returncode,
        )
