"""Maven test runner implementation."""

import re
from pathlib import Path

from .base import TestResult, TestRunner


class MavenRunner(TestRunner):
    """Test runner for Maven (Java/JUnit)."""

    @property
    def name(self) -> str:
        return "maven"

    def get_test_file_pattern(self) -> str:
        return "*Test.java"

    def get_test_file_name(self, source_name: str) -> str:
        """Generate test file name: Foo.java -> FooTest.java"""
        path = Path(source_name)
        return f"{path.stem}Test{path.suffix}"

    def run(self, test_file: Path) -> TestResult:
        """Run Maven tests."""
        # Maven runs all tests in the project, but we can specify a test class
        test_class = test_file.stem  # e.g., "CalculatorTest"

        command = [
            "mvn",
            "test",
            f"-Dtest={test_class}",
            "-q",  # Quiet mode for cleaner output
        ]

        exit_code, output = self._run_command(command)

        # Parse Maven/Surefire output for stats
        passed = 0
        failed = 0
        errors = 0

        # Look for summary line like "Tests run: 5, Failures: 1, Errors: 0, Skipped: 0"
        summary_match = re.search(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)",
            output,
        )

        if summary_match:
            total = int(summary_match.group(1))
            failed = int(summary_match.group(2))
            errors = int(summary_match.group(3))
            passed = total - failed - errors

        # Also check for "BUILD SUCCESS" or "BUILD FAILURE"
        if "BUILD SUCCESS" in output and exit_code == 0:
            success = True
        else:
            success = False

        return TestResult(
            success=success,
            output=output,
            passed=passed,
            failed=failed,
            errors=errors,
        )
