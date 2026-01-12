"""Jest test runner implementation."""

import re
from pathlib import Path

from .base import TestResult, TestRunner


class JestRunner(TestRunner):
    """Test runner for Jest (JavaScript/TypeScript)."""

    @property
    def name(self) -> str:
        return "jest"

    def get_test_file_pattern(self) -> str:
        return "*.test.{js,ts,jsx,tsx}"

    def get_test_file_name(self, source_name: str) -> str:
        """Generate test file name: foo.js -> foo.test.js"""
        path = Path(source_name)
        return f"{path.stem}.test{path.suffix}"

    def run(self, test_file: Path) -> TestResult:
        """Run Jest on the specified file."""
        command = [
            "npx",
            "jest",
            str(test_file),
            "--colors",
        ]

        exit_code, output = self._run_command(command)

        # Parse Jest output for stats
        passed = 0
        failed = 0
        errors = 0

        # Look for passed/failed counts in Jest output
        # Format can be "Tests: 5 passed" or "Tests: 2 failed, 3 passed"
        passed_match = re.search(r"(\d+) passed", output)
        failed_match = re.search(r"(\d+) failed", output)

        if passed_match:
            passed = int(passed_match.group(1))
        if failed_match:
            failed = int(failed_match.group(1))

        # Check for errors in output
        if "Error:" in output or "SyntaxError" in output:
            errors = 1

        return TestResult(
            success=exit_code == 0,
            output=output,
            passed=passed,
            failed=failed,
            errors=errors,
        )
