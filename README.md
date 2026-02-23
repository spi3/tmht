# tutr - Terminal Utility for Con(T)extual Responses

A stupid simple, AI-powered terminal assistant that generates commands from natural language.

## Documentation

Docs website: https://spi3.github.io/tutr/index.html

## What does it do?

Generates terminal commands from natural language queries.

``` bash
> tutr git create and switch to a new branch called testing

  git checkout -b testing
```

``` bash
> tutr go back to the previous directory

  cd -
```

## Installation

Requires Python 3.10+.

```bash
pipx install tutr
```

Or run it without installing:

```bash
uvx tutr
```

For development from source:

```bash
git clone https://github.com/spi3/tutr.git
cd tutr
uv sync
```

## Setup

On first run, tutr launches an interactive setup to select your provider, model, and API key:

```
$ tutr git "show recent commits"

Welcome to tutr! Let's get you set up.

Select your LLM provider:
  1. Gemini
  2. Anthropic
  3. OpenAI
  4. xAI
  5. Ollama (local, no API key needed)

  Enter choice (1-5): 1

Enter your Gemini API key:
  API key:

Select a model:
  1. Gemini 3 Flash (recommended)
  2. Gemini 2.0 Flash
  3. Gemini 2.5 Pro

  Enter choice (1-3): 1

Configuration saved to ~/.tutr/config.json
```

Setup is skipped if `~/.tutr/config.json` already exists or provider API key environment variables are set.

To re-run or modify configuration at any time:

```bash
tutr-cli configure
```

## Usage

```
tutr <command> <what you want to do>
```

## Auto-start in Every Terminal

`tutr` is an interactive shell wrapper. To launch it automatically for every new
interactive terminal, add this to your shell rc file.

### Bash (`~/.bashrc`)

```bash
if [[ $- == *i* ]] && [[ -z "${TUTR_AUTOSTARTED:-}" ]] && [[ -z "${TUTR_SKIP_AUTOSTART:-}" ]]; then
  export TUTR_AUTOSTARTED=1
  exec tutr
fi
```

### Zsh (`~/.zshrc`)

```zsh
if [[ -o interactive ]] && [[ -z "${TUTR_AUTOSTARTED:-}" ]] && [[ -z "${TUTR_SKIP_AUTOSTART:-}" ]]; then
  export TUTR_AUTOSTARTED=1
  exec tutr
fi
```

Notes:
- `TUTR_AUTOSTARTED` prevents recursion when `tutr` sources your normal rc file.
- Set `TUTR_SKIP_AUTOSTART=1` before opening a terminal to temporarily bypass autostart.
- Active wrapped shells show a prompt prefix (default `[tutr]`) and set `TUTR_ACTIVE=1`.
- Customize the prefix with `TUTR_PROMPT_PREFIX` (example: `export TUTR_PROMPT_PREFIX="[ai]"`).
- Use `tutr-cli ...` if you want the original one-shot command generator behavior.

### Examples

```bash
tutr git "create and switch to a new branch called testing"
tutr sed "replace all instances of 'foo' with 'bar' in myfile.txt"
tutr curl "http://example.com and display all request headers"
```

### Arguments

| Argument | Description |
|---|---|
| `command` | The terminal command to get help with (e.g., `git`, `sed`, `curl`) |
| `query` | What you want to do, in natural language |

### Options

| Flag | Description |
|---|---|
| `-h, --help` | Show help message |
| `-V, --version` | Show version |
| `-d, --debug` | Enable debug logging |
| `-e, --explain` | Show LLM explanation and source for the generated command |

## Configure Command

Use `configure` to update provider/model selection and config flags.

Interactive wizard:

```bash
tutr-cli configure
```

Non-interactive examples:

```bash
tutr-cli configure --provider openai --model openai/gpt-4o --show-explanation
tutr-cli configure --provider anthropic --model anthropic/claude-sonnet-4-6
tutr-cli configure --provider ollama --ollama-host http://localhost:11434
tutr-cli configure --disable-update-check
tutr-cli configure --clear-api-key
```

Security note: avoid passing secrets via `--api-key` because CLI args can be exposed in shell history and process listings. Prefer interactive `tutr-cli configure` prompts or provider API key environment variables.

### Configure Flags

| Flag | Description |
|---|---|
| `--interactive` | Run the interactive wizard (default when no other flags are given) |
| `--provider <name>` | LLM provider (`anthropic`, `gemini`, `ollama`, `openai`, `xai`) |
| `--model <id>` | Model ID in LiteLLM format (e.g. `openai/gpt-4o`) |
| `--api-key <key>` | Store a provider API key in config (not recommended — may leak via shell history) |
| `--clear-api-key` | Remove the stored API key from config |
| `--ollama-host <url>` | Set Ollama host URL (e.g. `http://localhost:11434`) |
| `--clear-ollama-host` | Remove the stored Ollama host from config |
| `--show-explanation` | Enable explanation output by default |
| `--hide-explanation` | Disable explanation output by default |
| `--enable-update-check` | Enable periodic update checks (default) |
| `--disable-update-check` | Disable periodic update checks |
| `--allow-execute` | In shell mode, allow prompting to auto-run tutr suggestions (default) |
| `--no-execute` | In shell mode, never prompt to auto-run tutr suggestions |

## Update Checks

`tutr` periodically checks PyPI for newer versions (at most once every 24 hours). When an update is available, it prints a notice to stderr with the suggested update command. In an interactive terminal it also offers to run the update immediately.

The check runs in the background and times out after 1.5 seconds so it never slows down normal usage. A timestamp cache is stored at `~/.tutr/update-check.json`.

To disable update checks permanently:

```bash
tutr-cli configure --disable-update-check
```

Or suppress checks for a single session:

```bash
TUTR_UPDATE_CHECK=0 tutr ...
```

## Data sent to model providers

When `tutr` calls an LLM API, it may send:

- Your natural-language query.
- Command reference context collected from `<command> --help` and/or `man <command>`.
- Basic system information (for example platform/OS details).
- In shell wrapper mode, up to 2048 characters of recent terminal output after a failed command.

If you use remote providers, treat this information as data transmitted to that provider. Avoid including secrets in commands, queries, or terminal output.

## Configuration

Config is stored in `~/.tutr/config.json`. Environment variables override the config file.

| Environment Variable | Description | Default |
|---|---|---|
| `TUTR_MODEL` | LLM model to use ([litellm format](https://docs.litellm.ai/docs/providers)) | `gemini/gemini-3-flash-preview` |
| `GEMINI_API_KEY` | Gemini API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `XAI_API_KEY` | xAI API key | — |
| `OLLAMA_HOST` | Ollama host URL override | `http://localhost:11434` |
| `TUTR_UPDATE_CHECK` | Enable (`1/true`) or disable (`0/false`) update checks | `true` |
| `TUTR_SHELL` | Override wrapper shell detection (`bash`, `zsh`, `pwsh`, or `powershell`) | auto-detected |

You can edit settings with `tutr-cli configure` or directly in `~/.tutr/config.json`.

## Development

Run all quality checks:

```bash
uv run poe check
```

Run tests only:

```bash
uv run pytest
```

Lint and format:

```bash
uv run ruff check .
uv run ruff format .
```
