"""Tests for test runners."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from proven.runners.base import TestRunner, TestResult
from proven.runners.pytest_runner import PytestRunner
from proven.runners.jest_runner import JestRunner
from proven.runners.maven_runner import MavenRunner


class TestTestResult:
    """Tests for the TestResult dataclass."""

    def test_is_red_when_failed(self):
        """Test is_red returns True when tests failed."""
        result = TestResult(success=False, output="FAILED", failed=1)
        assert result.is_red is True

    def test_is_red_when_errors(self):
        """Test is_red returns True when there are errors."""
        result = TestResult(success=False, output="ERROR", errors=1)
        assert result.is_red is True

    def test_is_green_when_passed(self):
        """Test is_green returns True when all tests pass."""
        result = TestResult(success=True, output="PASSED", passed=5, failed=0, errors=0)
        assert result.is_green is True

    def test_is_green_false_when_failed(self):
        """Test is_green returns False when tests failed."""
        result = TestResult(success=True, output="", passed=4, failed=1)
        assert result.is_green is False

    def test_is_red_and_green_mutually_exclusive(self):
        """Test that is_red and is_green are mutually exclusive."""
        passing = TestResult(success=True, output="", passed=1, failed=0, errors=0)
        failing = TestResult(success=False, output="", passed=0, failed=1, errors=0)

        assert passing.is_green and not passing.is_red
        assert failing.is_red and not failing.is_green


class TestPytestRunner:
    """Tests for the pytest runner."""

    def test_name(self):
        """Test runner name."""
        runner = PytestRunner()
        assert runner.name == "pytest"

    def test_get_test_file_pattern(self):
        """Test test file pattern."""
        runner = PytestRunner()
        assert runner.get_test_file_pattern() == "test_*.py"

    def test_get_test_file_name(self):
        """Test generating test file name from source."""
        runner = PytestRunner()

        assert runner.get_test_file_name("calculator.py") == "test_calculator.py"
        assert runner.get_test_file_name("utils.py") == "test_utils.py"

    def test_run_parses_passed_count(self, temp_cwd: Path):
        """Test that run parses passed test count."""
        runner = PytestRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            mock_run.return_value = (0, "5 passed in 0.1s")

            result = runner.run(temp_cwd / "test_example.py")

            assert result.success is True
            assert result.passed == 5

    def test_run_parses_failed_count(self, temp_cwd: Path):
        """Test that run parses failed test count."""
        runner = PytestRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            mock_run.return_value = (1, "2 failed, 3 passed in 0.2s")

            result = runner.run(temp_cwd / "test_example.py")

            assert result.success is False
            assert result.failed == 2
            assert result.passed == 3

    def test_run_parses_error_count(self, temp_cwd: Path):
        """Test that run parses error count."""
        runner = PytestRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            mock_run.return_value = (1, "1 error in 0.1s")

            result = runner.run(temp_cwd / "test_example.py")

            assert result.errors == 1


class TestJestRunner:
    """Tests for the Jest runner."""

    def test_name(self):
        """Test runner name."""
        runner = JestRunner()
        assert runner.name == "jest"

    def test_get_test_file_pattern(self):
        """Test test file pattern."""
        runner = JestRunner()
        assert "test" in runner.get_test_file_pattern()

    def test_get_test_file_name(self):
        """Test generating test file name from source."""
        runner = JestRunner()

        assert runner.get_test_file_name("calculator.js") == "calculator.test.js"
        assert runner.get_test_file_name("utils.ts") == "utils.test.ts"

    def test_run_parses_passed_count(self, temp_cwd: Path):
        """Test that run parses passed test count."""
        runner = JestRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            mock_run.return_value = (0, "Tests: 5 passed, 5 total")

            result = runner.run(temp_cwd / "example.test.js")

            assert result.success is True
            assert result.passed == 5

    def test_run_parses_failed_count(self, temp_cwd: Path):
        """Test that run parses failed test count."""
        runner = JestRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            mock_run.return_value = (1, "Tests: 2 failed, 3 passed, 5 total")

            result = runner.run(temp_cwd / "example.test.js")

            assert result.success is False
            assert result.failed == 2
            assert result.passed == 3


class TestMavenRunner:
    """Tests for the Maven runner."""

    def test_name(self):
        """Test runner name."""
        runner = MavenRunner()
        assert runner.name == "maven"

    def test_get_test_file_pattern(self):
        """Test test file pattern."""
        runner = MavenRunner()
        assert runner.get_test_file_pattern() == "*Test.java"

    def test_get_test_file_name(self):
        """Test generating test file name from source."""
        runner = MavenRunner()

        assert runner.get_test_file_name("Calculator.java") == "CalculatorTest.java"
        assert runner.get_test_file_name("Utils.java") == "UtilsTest.java"

    def test_run_parses_passed_count(self, temp_cwd: Path):
        """Test that run parses passed test count from Surefire output."""
        runner = MavenRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            mock_run.return_value = (0, "Tests run: 5, Failures: 0, Errors: 0, Skipped: 0\nBUILD SUCCESS")

            result = runner.run(temp_cwd / "CalculatorTest.java")

            assert result.success is True
            assert result.passed == 5
            assert result.failed == 0
            assert result.errors == 0

    def test_run_parses_failed_count(self, temp_cwd: Path):
        """Test that run parses failed test count from Surefire output."""
        runner = MavenRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            mock_run.return_value = (1, "Tests run: 5, Failures: 2, Errors: 0, Skipped: 0\nBUILD FAILURE")

            result = runner.run(temp_cwd / "CalculatorTest.java")

            assert result.success is False
            assert result.passed == 3
            assert result.failed == 2
            assert result.errors == 0

    def test_run_parses_error_count(self, temp_cwd: Path):
        """Test that run parses error count from Surefire output."""
        runner = MavenRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            mock_run.return_value = (1, "Tests run: 5, Failures: 1, Errors: 2, Skipped: 0\nBUILD FAILURE")

            result = runner.run(temp_cwd / "CalculatorTest.java")

            assert result.success is False
            assert result.passed == 2
            assert result.failed == 1
            assert result.errors == 2

    def test_run_build_success_required(self, temp_cwd: Path):
        """Test that success requires BUILD SUCCESS in output."""
        runner = MavenRunner(working_dir=temp_cwd)

        with patch.object(runner, "_run_command") as mock_run:
            # Exit code 0 but no BUILD SUCCESS
            mock_run.return_value = (0, "Tests run: 5, Failures: 0, Errors: 0")

            result = runner.run(temp_cwd / "CalculatorTest.java")

            assert result.success is False


class TestRunnerBaseClass:
    """Tests for the TestRunner base class."""

    def test_working_dir_defaults_to_cwd(self, temp_cwd: Path):
        """Test working directory defaults to current directory."""
        runner = PytestRunner()
        # Resolve both paths to handle macOS /private/var vs /var symlinks
        assert runner.working_dir.resolve() == temp_cwd.resolve()

    def test_working_dir_can_be_set(self, temp_dir: Path):
        """Test working directory can be explicitly set."""
        custom_dir = temp_dir / "custom"
        custom_dir.mkdir()

        runner = PytestRunner(working_dir=custom_dir)
        assert runner.working_dir == custom_dir

    def test_run_command_handles_timeout(self, temp_cwd: Path):
        """Test _run_command handles subprocess timeout."""
        runner = PytestRunner(working_dir=temp_cwd)

        with patch("proven.runners.base.subprocess.run") as mock_run:
            from subprocess import TimeoutExpired
            mock_run.side_effect = TimeoutExpired("cmd", 60)

            exit_code, output = runner._run_command(["pytest"])

            assert exit_code == 1
            assert "timed out" in output.lower()

    def test_run_command_handles_missing_command(self, temp_cwd: Path):
        """Test _run_command handles missing command."""
        runner = PytestRunner(working_dir=temp_cwd)

        with patch("proven.runners.base.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("pytest not found")

            exit_code, output = runner._run_command(["pytest"])

            assert exit_code == 1
            assert "not found" in output.lower()
