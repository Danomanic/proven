"""Abstract base class for test runners."""

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TestResult:
    """Result of running tests."""

    success: bool
    output: str
    passed: int = 0
    failed: int = 0
    errors: int = 0

    @property
    def is_red(self) -> bool:
        """Check if tests are in RED state (failing)."""
        return not self.success or self.failed > 0 or self.errors > 0

    @property
    def is_green(self) -> bool:
        """Check if tests are in GREEN state (passing)."""
        return self.success and self.failed == 0 and self.errors == 0


class TestRunner(ABC):
    """Abstract base class for test runners."""

    def __init__(self, working_dir: Optional[Path] = None):
        self.working_dir = working_dir or Path.cwd()

    @abstractmethod
    def run(self, test_file: Path) -> TestResult:
        """Run tests in the specified file.

        Args:
            test_file: Path to the test file

        Returns:
            TestResult with the outcome
        """
        pass

    @abstractmethod
    def get_test_file_pattern(self) -> str:
        """Get the glob pattern for test files."""
        pass

    @abstractmethod
    def get_test_file_name(self, source_name: str) -> str:
        """Generate a test file name from a source file name."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the runner name."""
        pass

    def _run_command(self, command: list[str]) -> tuple[int, str]:
        """Run a shell command and return exit code and output."""
        try:
            result = subprocess.run(
                command,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, "Test execution timed out"
        except FileNotFoundError as e:
            return 1, f"Command not found: {e}"
