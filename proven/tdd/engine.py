"""TDD workflow engine that orchestrates the Red-Green-Refactor cycle."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ..providers.base import LLMProvider
from ..runners.base import TestResult, TestRunner
from .prompts import TDDPrompts


class TDDPhase(Enum):
    """Phases of the TDD cycle."""

    RED = "red"  # Write failing tests
    GREEN = "green"  # Write code to pass tests
    REFACTOR = "refactor"  # Improve code quality


@dataclass
class TDDResult:
    """Result of a TDD workflow execution."""

    test_code: str
    implementation_code: str
    test_file: Path
    source_file: Path
    final_test_result: TestResult
    phase: TDDPhase


class TDDEngine:
    """Orchestrates the TDD workflow: Red -> Green -> Refactor."""

    def __init__(
        self,
        provider: LLMProvider,
        runner: TestRunner,
        console: Optional[Console] = None,
        language: str = "python",
    ):
        self.provider = provider
        self.runner = runner
        self.console = console or Console()
        self.language = language
        self.prompts = TDDPrompts()

    async def run(
        self,
        request: str,
        test_file: Path,
        source_file: Path,
        on_approval: Optional[Callable[[str, str], bool]] = None,
        max_iterations: int = 3,
    ) -> TDDResult:
        """Execute the full TDD workflow.

        Args:
            request: User's description of what to build
            test_file: Where to write tests
            source_file: Where to write implementation
            on_approval: Callback to ask user for approval (phase, code) -> bool
            max_iterations: Max attempts to make tests pass

        Returns:
            TDDResult with generated code and test results
        """
        # Phase 1: RED - Generate tests
        self.console.print(
            Panel("[bold red]PHASE 1: RED[/bold red] - Generating tests first...", border_style="red")
        )

        test_code = await self._generate_tests(request)

        # Show tests and ask for approval
        self._display_code(test_code, "Tests", "python")

        if on_approval and not on_approval("tests", test_code):
            self.console.print("[yellow]Tests not approved. Aborting.[/yellow]")
            raise RuntimeError("User did not approve tests")

        # Write test file
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(test_code)
        self.console.print(f"[dim]Tests written to {test_file}[/dim]")

        # Run tests - they should FAIL (no implementation yet)
        self.console.print("\n[bold]Running tests (expecting failure)...[/bold]")
        red_result = self.runner.run(test_file)

        if red_result.is_green:
            self.console.print(
                "[yellow]Warning: Tests passed without implementation. "
                "Tests may not be testing the right thing.[/yellow]"
            )
        else:
            self.console.print(
                f"[green]Tests fail as expected (RED phase complete)[/green]\n"
                f"[dim]{red_result.failed} failed, {red_result.errors} errors[/dim]"
            )

        # Phase 2: GREEN - Generate implementation
        self.console.print(
            Panel("[bold green]PHASE 2: GREEN[/bold green] - Generating implementation...", border_style="green")
        )

        implementation_code = await self._generate_implementation(request, test_code)

        # Show implementation and ask for approval
        self._display_code(implementation_code, "Implementation", "python")

        if on_approval and not on_approval("implementation", implementation_code):
            self.console.print("[yellow]Implementation not approved. Aborting.[/yellow]")
            raise RuntimeError("User did not approve implementation")

        # Write source file
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(implementation_code)
        self.console.print(f"[dim]Implementation written to {source_file}[/dim]")

        # Run tests - they should PASS now
        iteration = 0
        green_result = self.runner.run(test_file)

        while green_result.is_red and iteration < max_iterations:
            iteration += 1
            self.console.print(
                f"\n[yellow]Tests still failing. Iteration {iteration}/{max_iterations}...[/yellow]"
            )
            self.console.print(f"[dim]{green_result.output}[/dim]")

            # Ask LLM to fix the implementation
            implementation_code = await self._fix_implementation(
                request, test_code, implementation_code, green_result.output
            )
            source_file.write_text(implementation_code)

            green_result = self.runner.run(test_file)

        if green_result.is_green:
            self.console.print(
                f"\n[bold green]All tests pass! (GREEN phase complete)[/bold green]\n"
                f"[dim]{green_result.passed} passed[/dim]"
            )
        else:
            self.console.print(
                f"\n[bold red]Tests still failing after {max_iterations} iterations[/bold red]"
            )
            self.console.print(f"[dim]{green_result.output}[/dim]")

        return TDDResult(
            test_code=test_code,
            implementation_code=implementation_code,
            test_file=test_file,
            source_file=source_file,
            final_test_result=green_result,
            phase=TDDPhase.GREEN if green_result.is_green else TDDPhase.RED,
        )

    async def _generate_tests(self, request: str) -> str:
        """Generate test code for the request."""
        system = self.prompts.test_generation(self.runner.name, self.language)
        prompt = f"Write tests for the following requirement:\n\n{request}"

        response = await self.provider.generate(prompt, system)
        return self.prompts.extract_code_block(response, self.language)

    async def _generate_implementation(self, request: str, test_code: str) -> str:
        """Generate implementation code to pass the tests."""
        system = self.prompts.implementation(self.runner.name, self.language)
        prompt = f"""Write implementation code to pass these tests.

Original requirement:
{request}

Tests to pass:
```{self.language}
{test_code}
```

Write the implementation:"""

        response = await self.provider.generate(prompt, system)
        return self.prompts.extract_code_block(response, self.language)

    async def _fix_implementation(
        self, request: str, test_code: str, current_impl: str, error_output: str
    ) -> str:
        """Fix implementation based on test failures."""
        system = self.prompts.implementation(self.runner.name, self.language)
        prompt = f"""The tests are failing. Fix the implementation.

Original requirement:
{request}

Tests:
```{self.language}
{test_code}
```

Current implementation:
```{self.language}
{current_impl}
```

Test failure output:
{error_output}

Write the corrected implementation:"""

        response = await self.provider.generate(prompt, system)
        return self.prompts.extract_code_block(response, self.language)

    def _display_code(self, code: str, title: str, language: str) -> None:
        """Display code with syntax highlighting."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title=title, border_style="blue"))
