"""Tests for the TDD engine."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from proven.tdd.engine import TDDEngine, TDDPhase, TDDResult
from proven.tdd.prompts import TDDPrompts
from proven.runners.base import TestResult


class TestTDDPrompts:
    """Tests for TDD prompts."""

    def test_test_generation_prompt_includes_framework(self):
        """Test that test generation prompt includes the framework name."""
        prompt = TDDPrompts.test_generation("pytest", "python")

        assert "pytest" in prompt
        assert "python" in prompt
        assert "test" in prompt.lower()

    def test_implementation_prompt_mentions_tests(self):
        """Test that implementation prompt references tests."""
        prompt = TDDPrompts.implementation("pytest", "python")

        assert "test" in prompt.lower()
        assert "pass" in prompt.lower()

    def test_refactor_prompt_mentions_keeping_tests_green(self):
        """Test that refactor prompt mentions keeping tests passing."""
        prompt = TDDPrompts.refactor()

        assert "test" in prompt.lower()
        assert "pass" in prompt.lower()

    def test_extract_code_block_python(self):
        """Test extracting Python code from markdown."""
        response = """Here's the code:

```python
def add(a, b):
    return a + b
```

That's all!"""

        code = TDDPrompts.extract_code_block(response, "python")

        assert "def add(a, b):" in code
        assert "return a + b" in code
        assert "```" not in code

    def test_extract_code_block_generic(self):
        """Test extracting code from generic code block."""
        response = """```
def example():
    pass
```"""

        code = TDDPrompts.extract_code_block(response, "python")

        assert "def example():" in code

    def test_extract_code_block_no_block(self):
        """Test extracting code when there's no code block."""
        response = "Just some plain text without code blocks"

        code = TDDPrompts.extract_code_block(response, "python")

        assert code == response.strip()


class TestTDDEngine:
    """Tests for the TDD engine."""

    @pytest.fixture
    def engine(self, mock_llm_provider, mock_test_runner):
        """Create a TDD engine with mocked dependencies."""
        console = MagicMock()
        return TDDEngine(
            provider=mock_llm_provider,
            runner=mock_test_runner,
            console=console,
            language="python",
        )

    @pytest.mark.asyncio
    async def test_run_generates_tests_first(
        self, engine, mock_llm_provider, temp_cwd: Path
    ):
        """Test that run() generates tests before implementation."""
        test_file = temp_cwd / "tests" / "test_example.py"
        source_file = temp_cwd / "src" / "example.py"

        # Set up mock to return test code first, then implementation
        mock_llm_provider.generate = AsyncMock(
            side_effect=[
                "```python\ndef test_add():\n    assert add(1, 2) == 3\n```",
                "```python\ndef add(a, b):\n    return a + b\n```",
            ]
        )

        result = await engine.run(
            request="Create an add function",
            test_file=test_file,
            source_file=source_file,
            on_approval=lambda phase, code: True,
        )

        # Verify tests were generated first
        calls = mock_llm_provider.generate.call_args_list
        assert len(calls) == 2

        # First call should be for tests
        first_call_prompt = calls[0][0][0]
        assert "test" in first_call_prompt.lower()

    @pytest.mark.asyncio
    async def test_run_writes_test_file(
        self, engine, mock_llm_provider, temp_cwd: Path
    ):
        """Test that run() writes the test file."""
        test_file = temp_cwd / "tests" / "test_example.py"
        source_file = temp_cwd / "src" / "example.py"

        mock_llm_provider.generate = AsyncMock(
            side_effect=[
                "```python\ndef test_example():\n    pass\n```",
                "```python\ndef example():\n    pass\n```",
            ]
        )

        await engine.run(
            request="Create example",
            test_file=test_file,
            source_file=source_file,
            on_approval=lambda phase, code: True,
        )

        assert test_file.exists()
        content = test_file.read_text()
        assert "def test_example" in content

    @pytest.mark.asyncio
    async def test_run_writes_source_file(
        self, engine, mock_llm_provider, temp_cwd: Path
    ):
        """Test that run() writes the source file."""
        test_file = temp_cwd / "tests" / "test_example.py"
        source_file = temp_cwd / "src" / "example.py"

        mock_llm_provider.generate = AsyncMock(
            side_effect=[
                "```python\ndef test_example():\n    pass\n```",
                "```python\ndef example():\n    return 42\n```",
            ]
        )

        await engine.run(
            request="Create example",
            test_file=test_file,
            source_file=source_file,
            on_approval=lambda phase, code: True,
        )

        assert source_file.exists()
        content = source_file.read_text()
        assert "def example" in content

    @pytest.mark.asyncio
    async def test_run_aborts_if_tests_not_approved(
        self, engine, mock_llm_provider, temp_cwd: Path
    ):
        """Test that run() aborts if user doesn't approve tests."""
        test_file = temp_cwd / "tests" / "test_example.py"
        source_file = temp_cwd / "src" / "example.py"

        mock_llm_provider.generate = AsyncMock(
            return_value="```python\ndef test_example():\n    pass\n```"
        )

        with pytest.raises(RuntimeError, match="not approve"):
            await engine.run(
                request="Create example",
                test_file=test_file,
                source_file=source_file,
                on_approval=lambda phase, code: False,
            )

    @pytest.mark.asyncio
    async def test_run_returns_green_on_success(
        self, engine, mock_llm_provider, mock_test_runner, temp_cwd: Path
    ):
        """Test that run() returns GREEN phase on success."""
        test_file = temp_cwd / "tests" / "test_example.py"
        source_file = temp_cwd / "src" / "example.py"

        mock_llm_provider.generate = AsyncMock(
            side_effect=[
                "```python\ndef test_example():\n    pass\n```",
                "```python\ndef example():\n    pass\n```",
            ]
        )

        # Runner returns fail then pass
        mock_test_runner.run = MagicMock(
            side_effect=[
                TestResult(success=False, output="FAILED", failed=1),
                TestResult(success=True, output="PASSED", passed=1),
            ]
        )

        result = await engine.run(
            request="Create example",
            test_file=test_file,
            source_file=source_file,
            on_approval=lambda phase, code: True,
        )

        assert result.phase == TDDPhase.GREEN
        assert result.final_test_result.is_green

    @pytest.mark.asyncio
    async def test_run_retries_on_failure(
        self, engine, mock_llm_provider, mock_test_runner, temp_cwd: Path
    ):
        """Test that run() retries when tests fail."""
        test_file = temp_cwd / "tests" / "test_example.py"
        source_file = temp_cwd / "src" / "example.py"

        # First generate tests, then implementation, then fix
        mock_llm_provider.generate = AsyncMock(
            side_effect=[
                "```python\ndef test_example():\n    pass\n```",
                "```python\ndef example():\n    pass  # wrong\n```",
                "```python\ndef example():\n    return 42  # fixed\n```",
            ]
        )

        # Fail first implementation, then pass
        mock_test_runner.run = MagicMock(
            side_effect=[
                TestResult(success=False, output="RED", failed=1),  # Initial
                TestResult(success=False, output="FAILED", failed=1),  # First impl
                TestResult(success=True, output="PASSED", passed=1),  # After fix
            ]
        )

        result = await engine.run(
            request="Create example",
            test_file=test_file,
            source_file=source_file,
            on_approval=lambda phase, code: True,
        )

        # Should have called generate 3 times (tests + impl + fix)
        assert mock_llm_provider.generate.call_count == 3
        assert result.phase == TDDPhase.GREEN


class TestTDDResult:
    """Tests for the TDDResult dataclass."""

    def test_result_contains_all_fields(self, temp_cwd: Path):
        """Test that TDDResult contains all expected fields."""
        result = TDDResult(
            test_code="def test(): pass",
            implementation_code="def impl(): pass",
            test_file=temp_cwd / "test.py",
            source_file=temp_cwd / "impl.py",
            final_test_result=TestResult(success=True, output="", passed=1),
            phase=TDDPhase.GREEN,
        )

        assert result.test_code == "def test(): pass"
        assert result.implementation_code == "def impl(): pass"
        assert result.phase == TDDPhase.GREEN
