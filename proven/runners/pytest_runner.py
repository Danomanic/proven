"""Pytest test runner implementation."""

import re
from pathlib import Path

from .base import TestResult, TestRunner


class PytestRunner(TestRunner):
    """Test runner for pytest."""

    @property
    def name(self) -> str:
        return "pytest"

    def get_test_file_pattern(self) -> str:
        return "test_*.py"

    def get_test_file_name(self, source_name: str) -> str:
        """Generate test file name: foo.py -> test_foo.py"""
        stem = Path(source_name).stem
        return f"test_{stem}.py"

    def run(self, test_file: Path) -> TestResult:
        """Run pytest on the specified file."""
        command = [
            "python",
            "-m",
            "pytest",
            str(test_file),
            "-v",
            "--tb=short",
        ]

        exit_code, output = self._run_command(command)

        # Parse pytest output for stats
        passed = 0
        failed = 0
        errors = 0

        # Look for summary line like "1 passed, 2 failed, 1 error"
        summary_match = re.search(
            r"(\d+) passed|(\d+) failed|(\d+) error",
            output,
        )

        if summary_match:
            passed_match = re.search(r"(\d+) passed", output)
            failed_match = re.search(r"(\d+) failed", output)
            error_match = re.search(r"(\d+) error", output)

            if passed_match:
                passed = int(passed_match.group(1))
            if failed_match:
                failed = int(failed_match.group(1))
            if error_match:
                errors = int(error_match.group(1))

        return TestResult(
            success=exit_code == 0,
            output=output,
            passed=passed,
            failed=failed,
            errors=errors,
        )
