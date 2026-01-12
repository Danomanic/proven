# Proven

**Test-first code generation with LLMs.**

Proven enforces Test-Driven Development by generating tests *before* implementation. Every piece of code is proven to work before it's written.

## Why Proven?

Traditional AI code generation writes implementation first, then maybe tests. Proven flips this:

1. **Red** - Generate comprehensive tests that define the behavior
2. **Green** - Generate minimal code to make tests pass
3. **Refactor** - Improve with confidence (tests keep you safe)

The result? Code that's tested from the start, with clear specifications and fewer bugs.

## Features

- **Strict TDD Enforcement** - Tests are always generated first
- **Interactive Mode** - REPL-style interface for iterative development
- **Multi-Provider Support** - Claude, GPT-4, Gemini, or local models via Ollama
- **Configurable Frameworks** - pytest, Jest, and more
- **Auto-Retry** - Automatically fixes implementation if tests fail
- **API Key Management** - Prompts for keys and saves them securely

## Installation

```bash
# Clone the repo
git clone https://github.com/Danomanic/proven.git
cd proven

# Install
pip install -e .
```

## Quick Start

```bash
# Launch interactive mode
proven
```

```
  ____
 |  _ \ _ __ _____   _____ _ __
 | |_) | '__/ _ \ \ / / _ \ '_ \
 |  __/| | | (_) \ V /  __/ | | |
 |_|   |_|  \___/ \_/ \___|_| |_|

Test-first code generation with LLMs

Provider: claude | Model: claude-sonnet-4-20250514
Test framework: pytest

Type /help for commands, or describe what you want to build.

> Create a function that validates email addresses
```

If no API key is configured, Proven will prompt you:

```
No API key found for claude.
You can also set the ANTHROPIC_API_KEY environment variable.

Enter your claude API key: ********
Save this API key to your config? [y/N]: y
```

## Usage

### Interactive Mode

Just run `proven` to start an interactive session:

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/config` | Show current configuration |
| `/provider <name>` | Switch provider (claude, openai, google, ollama) |
| `/framework <name>` | Switch test framework (pytest, jest) |
| `/quit` | Exit |

### CLI Commands

```bash
# Generate with TDD
proven generate "Create a function that checks if a number is prime"

# Specify module name
proven generate "Calculate fibonacci" --name fibonacci

# Custom directories
proven generate "Parse config" --test-dir tests/unit --source-dir lib

# Skip approval prompts
proven generate "Add two numbers" --yes

# Configuration
proven config show
proven config set provider openai
proven config set test-framework jest

# Initialize project config
proven init --provider claude --test-framework pytest
```

## Configuration

### Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
```

### Config Files

**Global** (`~/.proven/config.yaml`):

```yaml
provider: claude
model: claude-sonnet-4-20250514
test_framework: pytest
test_directory: tests
source_directory: src
```

**Project** (`.proven.yaml` - overrides global):

```yaml
provider: openai
test_framework: jest
```

## Supported Providers

| Provider | Models | Value |
|----------|--------|-------|
| Anthropic | Claude Sonnet, Opus, Haiku | `claude` |
| OpenAI | GPT-4o, GPT-4, GPT-3.5 | `openai` |
| Google | Gemini 2.0 Flash, Pro | `google` |
| Ollama | Llama, CodeLlama, Mistral | `ollama` |

### Using Local Models (Ollama)

```yaml
provider: ollama
ollama:
  base_url: http://localhost:11434
  model: codellama
```

## Supported Test Frameworks

| Framework | Language | Value |
|-----------|----------|-------|
| pytest | Python | `pytest` |
| Jest | JavaScript/TypeScript | `jest` |
| Maven | Java (JUnit) | `maven` |

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  1. RED PHASE                                               │
│  • LLM generates comprehensive tests                        │
│  • You review and approve                                   │
│  • Tests run and FAIL (no implementation yet)               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. GREEN PHASE                                             │
│  • LLM generates minimal implementation                     │
│  • You review and approve                                   │
│  • Tests run and PASS                                       │
│  • If tests fail, LLM retries (up to 3x)                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. DONE                                                    │
│  • Test file: tests/test_<name>.py                          │
│  • Source file: src/<name>.py                               │
│  • All tests passing                                        │
└─────────────────────────────────────────────────────────────┘
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v
```

## Project Structure

```
proven/
├── __init__.py
├── main.py              # CLI entry point
├── config.py            # Configuration management
├── providers/           # LLM provider implementations
│   ├── base.py          # Abstract interface
│   ├── anthropic.py     # Claude
│   ├── openai.py        # GPT
│   ├── google.py        # Gemini
│   └── ollama.py        # Local models
├── runners/             # Test runner implementations
│   ├── base.py          # Abstract interface
│   ├── pytest_runner.py
│   ├── jest_runner.py
│   └── maven_runner.py
└── tdd/                 # TDD engine
    ├── engine.py        # Workflow orchestration
    └── prompts.py       # LLM prompts for TDD
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest tests/ -v`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Pydantic](https://pydantic.dev/) - Configuration validation
