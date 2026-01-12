"""CLI entry point for Proven."""

import warnings

# Suppress deprecation warnings from dependencies on older Python versions
warnings.filterwarnings("ignore", category=FutureWarning, module="google")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google")
warnings.filterwarnings("ignore", message=".*urllib3.*OpenSSL.*")

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .config import Config, load_config, save_global_config, get_global_config_path
from .providers import AnthropicProvider, GoogleProvider, OllamaProvider, OpenAIProvider
from .providers.base import LLMProvider
from .runners import JestRunner, PytestRunner
from .runners.base import TestRunner
from .tdd.engine import TDDEngine

app = typer.Typer(
    name="proven",
    help="Test-first code generation with LLMs",
    invoke_without_command=True,
)
config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")

console = Console()


def get_api_key_with_prompt(config: Config, provider_name: str) -> Optional[str]:
    """Get API key for provider, prompting user if not set."""
    api_key = config.get_api_key(provider_name)

    # Ollama doesn't need an API key
    if provider_name == "ollama":
        return None

    if not api_key:
        env_var_map = {
            "claude": "ANTHROPIC_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gpt": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
            "gemini": "GOOGLE_API_KEY",
        }
        env_var = env_var_map.get(provider_name.lower(), "API_KEY")

        console.print(f"\n[yellow]No API key found for {provider_name}.[/yellow]")
        console.print(f"[dim]You can also set the {env_var} environment variable.[/dim]\n")

        api_key = Prompt.ask(f"Enter your {provider_name} API key", password=True)

        if not api_key:
            console.print("[red]API key is required.[/red]")
            raise typer.Exit(1)

        # Ask if they want to save it
        if Confirm.ask("Save this API key to your config?", default=False):
            if provider_name in ("claude", "anthropic"):
                config.api_keys.anthropic = api_key
            elif provider_name in ("openai", "gpt"):
                config.api_keys.openai = api_key
            elif provider_name in ("google", "gemini"):
                config.api_keys.google = api_key
            save_global_config(config)
            console.print("[green]API key saved to config.[/green]\n")

    return api_key


def get_provider(config: Config) -> LLMProvider:
    """Get the configured LLM provider."""
    provider_name = config.provider.lower()
    model = config.get_model_for_provider(provider_name)
    api_key = get_api_key_with_prompt(config, provider_name)

    if provider_name in ("claude", "anthropic"):
        return AnthropicProvider(api_key=api_key, model=model)
    elif provider_name in ("openai", "gpt"):
        return OpenAIProvider(api_key=api_key, model=model)
    elif provider_name in ("google", "gemini"):
        return GoogleProvider(api_key=api_key, model=model)
    elif provider_name == "ollama":
        return OllamaProvider(
            model=model,
            base_url=config.ollama.base_url,
        )
    else:
        raise typer.BadParameter(f"Unknown provider: {provider_name}")


def get_runner(config: Config) -> TestRunner:
    """Get the configured test runner."""
    framework = config.test_framework.lower()

    if framework == "pytest":
        return PytestRunner()
    elif framework == "jest":
        return JestRunner()
    else:
        raise typer.BadParameter(f"Unknown test framework: {framework}")


def approval_callback(phase: str, code: str) -> bool:
    """Ask user to approve generated code."""
    return Confirm.ask(f"\n[bold]Approve the {phase}?[/bold]", default=True)


def get_language_for_framework(framework: str) -> str:
    """Get programming language for a test framework."""
    if framework in ("pytest", "unittest"):
        return "python"
    elif framework in ("jest", "mocha", "vitest"):
        return "javascript"
    return "python"


def run_tdd_workflow(description: str, name: Optional[str] = None, no_confirm: bool = False) -> bool:
    """Run the TDD workflow for a given description. Returns True on success."""
    config = load_config()

    # Determine file names and paths
    if not name:
        name = description.lower().split()[0]
        name = "".join(c for c in name if c.isalnum())

    test_directory = Path(config.test_directory)
    source_directory = Path(config.source_directory)
    runner = get_runner(config)
    language = get_language_for_framework(config.test_framework)

    # Determine file names based on test framework
    if config.test_framework == "pytest":
        test_file = test_directory / f"test_{name}.py"
        source_file = source_directory / f"{name}.py"
    elif config.test_framework == "jest":
        test_file = test_directory / f"{name}.test.js"
        source_file = source_directory / f"{name}.js"
    else:
        test_file = test_directory / f"test_{name}.py"
        source_file = source_directory / f"{name}.py"

    console.print(f"\n[dim]Provider: {config.provider} | Framework: {config.test_framework}[/dim]")
    console.print(f"[dim]Tests: {test_file} | Source: {source_file}[/dim]\n")

    provider = get_provider(config)
    engine = TDDEngine(
        provider=provider,
        runner=runner,
        console=console,
        language=language,
    )

    on_approval = None if no_confirm else approval_callback

    try:
        result = asyncio.run(
            engine.run(
                request=description,
                test_file=test_file,
                source_file=source_file,
                on_approval=on_approval,
            )
        )

        if result.final_test_result.is_green:
            console.print("\n[bold green]TDD cycle complete![/bold green]")
            console.print(f"  Tests: {result.test_file}")
            console.print(f"  Source: {result.source_file}")
            return True
        else:
            console.print("\n[bold yellow]TDD cycle incomplete - tests still failing[/bold yellow]")
            return False

    except RuntimeError as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        return False


def print_banner() -> None:
    """Print the welcome banner."""
    banner = r"""[bold cyan]
  ____
 |  _ \ _ __ _____   _____ _ __
 | |_) | '__/ _ \ \ / / _ \ '_ \
 |  __/| | | (_) \ V /  __/ | | |
 |_|   |_|  \___/ \_/ \___|_| |_|
[/bold cyan]
[dim]Test-first code generation with LLMs[/dim]
"""
    console.print(banner)


def print_help() -> None:
    """Print interactive mode help."""
    console.print("""
[bold]Commands:[/bold]
  [cyan]/help[/cyan]      Show this help message
  [cyan]/config[/cyan]    Show current configuration
  [cyan]/quit[/cyan]      Exit the CLI

[bold]Usage:[/bold]
  Just type what you want to build and press Enter.
  The CLI will generate tests first, then implementation.

[bold]Examples:[/bold]
  [dim]> Create a function that validates email addresses[/dim]
  [dim]> Build a class that manages a shopping cart[/dim]
  [dim]> Write a function to parse CSV files[/dim]
""")


def interactive_mode() -> None:
    """Run the interactive REPL mode."""
    print_banner()

    config = load_config()
    console.print(f"[dim]Provider: {config.provider} | Model: {config.get_model_for_provider(config.provider)}[/dim]")
    console.print(f"[dim]Test framework: {config.test_framework}[/dim]")
    console.print("\n[dim]Type /help for commands, or describe what you want to build.[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]>[/bold cyan]").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd in ("/quit", "/exit", "/q"):
                    console.print("[dim]Goodbye![/dim]")
                    break
                elif cmd in ("/help", "/h", "/?"):
                    print_help()
                elif cmd in ("/config", "/c"):
                    config = load_config()
                    console.print(f"\n[bold]Configuration:[/bold]")
                    console.print(f"  Provider: {config.provider}")
                    console.print(f"  Model: {config.get_model_for_provider(config.provider)}")
                    console.print(f"  Test framework: {config.test_framework}")
                    console.print(f"  Test directory: {config.test_directory}")
                    console.print(f"  Source directory: {config.source_directory}\n")
                elif cmd.startswith("/provider "):
                    new_provider = user_input.split(" ", 1)[1].strip()
                    config = load_config()
                    config.provider = new_provider
                    save_global_config(config)
                    console.print(f"[green]Provider set to: {new_provider}[/green]\n")
                elif cmd.startswith("/framework "):
                    new_framework = user_input.split(" ", 1)[1].strip()
                    config = load_config()
                    config.test_framework = new_framework
                    save_global_config(config)
                    console.print(f"[green]Test framework set to: {new_framework}[/green]\n")
                else:
                    console.print(f"[yellow]Unknown command: {user_input}[/yellow]")
                    console.print("[dim]Type /help for available commands[/dim]\n")
                continue

            # Run TDD workflow
            run_tdd_workflow(user_input)
            console.print()  # Add spacing after workflow

        except KeyboardInterrupt:
            console.print("\n[dim]Use /quit to exit[/dim]")
        except EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            break


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Proven - Test-first code generation with LLMs."""
    if ctx.invoked_subcommand is None:
        interactive_mode()


@app.command()
def generate(
    description: str = typer.Argument(..., help="Description of what to build"),
    name: str = typer.Option(None, "--name", "-n", help="Name for the module/function"),
    test_dir: str = typer.Option(None, "--test-dir", "-t", help="Test directory"),
    source_dir: str = typer.Option(None, "--source-dir", "-s", help="Source directory"),
    no_confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
) -> None:
    """Generate code using TDD methodology.

    Writes tests first, runs them (expecting failure), then generates implementation.
    """
    config = load_config()

    # Determine file names and paths
    if not name:
        name = description.lower().split()[0]
        name = "".join(c for c in name if c.isalnum())

    test_directory = Path(test_dir or config.test_directory)
    source_directory = Path(source_dir or config.source_directory)

    runner = get_runner(config)

    # Determine file names based on test framework
    if config.test_framework == "pytest":
        test_file = test_directory / f"test_{name}.py"
        source_file = source_directory / f"{name}.py"
        language = "python"
    elif config.test_framework == "jest":
        test_file = test_directory / f"{name}.test.js"
        source_file = source_directory / f"{name}.js"
        language = "javascript"
    else:
        test_file = test_directory / f"test_{name}.py"
        source_file = source_directory / f"{name}.py"
        language = "python"

    console.print(f"\n[bold]TDD Code Generation[/bold]")
    console.print(f"[dim]Provider: {config.provider}[/dim]")
    console.print(f"[dim]Test framework: {config.test_framework}[/dim]")
    console.print(f"[dim]Test file: {test_file}[/dim]")
    console.print(f"[dim]Source file: {source_file}[/dim]\n")

    provider = get_provider(config)
    engine = TDDEngine(
        provider=provider,
        runner=runner,
        console=console,
        language=language,
    )

    on_approval = None if no_confirm else approval_callback

    try:
        result = asyncio.run(
            engine.run(
                request=description,
                test_file=test_file,
                source_file=source_file,
                on_approval=on_approval,
            )
        )

        if result.final_test_result.is_green:
            console.print("\n[bold green]TDD cycle complete![/bold green]")
            console.print(f"  Tests: {result.test_file}")
            console.print(f"  Source: {result.source_file}")
        else:
            console.print("\n[bold yellow]TDD cycle incomplete - tests still failing[/bold yellow]")
            raise typer.Exit(1)

    except RuntimeError as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def init(
    provider: str = typer.Option("claude", help="Default LLM provider"),
    test_framework: str = typer.Option("pytest", help="Test framework to use"),
) -> None:
    """Initialize Proven configuration in current project."""
    from .config import save_project_config

    config = Config(
        provider=provider,
        test_framework=test_framework,
    )

    save_project_config(config)
    console.print("[green]Created .proven.yaml in current directory[/green]")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    config = load_config()

    console.print("\n[bold]Current Configuration:[/bold]")
    console.print(f"  Provider: {config.provider}")
    console.print(f"  Model: {config.get_model_for_provider(config.provider)}")
    console.print(f"  Test framework: {config.test_framework}")
    console.print(f"  Test directory: {config.test_directory}")
    console.print(f"  Source directory: {config.source_directory}")

    # Show API key status (without revealing keys)
    console.print("\n[bold]API Keys:[/bold]")
    console.print(f"  Anthropic: {'[green]set[/green]' if config.api_keys.anthropic else '[red]not set[/red]'}")
    console.print(f"  OpenAI: {'[green]set[/green]' if config.api_keys.openai else '[red]not set[/red]'}")
    console.print(f"  Google: {'[green]set[/green]' if config.api_keys.google else '[red]not set[/red]'}")

    console.print(f"\n[dim]Global config: {get_global_config_path()}[/dim]")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (provider, model, test-framework)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    config = load_config()

    key_normalized = key.lower().replace("-", "_")

    if key_normalized == "provider":
        config.provider = value
    elif key_normalized == "model":
        config.model = value
    elif key_normalized == "test_framework":
        config.test_framework = value
    elif key_normalized == "test_directory":
        config.test_directory = value
    elif key_normalized == "source_directory":
        config.source_directory = value
    else:
        console.print(f"[red]Unknown config key: {key}[/red]")
        raise typer.Exit(1)

    save_global_config(config)
    console.print(f"[green]Set {key} = {value}[/green]")


if __name__ == "__main__":
    app()
