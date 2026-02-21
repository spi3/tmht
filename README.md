# tutr - Terminal Utility for Con(T)extual Responses

A stupid simple, AI-powered terminal assistant that generates commands from natural language.

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
git clone https://github.com/spi/tutr.git
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
  4. Ollama (local, no API key needed)

  Enter choice (1-4): 1

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

## Usage

```
tutr <command> <what you want to do>
```

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

## Configuration

Config is stored in `~/.tutr/config.json`. Environment variables override the config file.

| Environment Variable | Description | Default |
|---|---|---|
| `TUTR_MODEL` | LLM model to use ([litellm format](https://docs.litellm.ai/docs/providers)) | `gemini/gemini-3-flash-preview` |
| `GEMINI_API_KEY` | Gemini API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |

You can also enable command explanations persistently in `~/.tutr/config.json`:

```json
{
  "show_explanation": true
}
```

To re-run setup, delete the config file:

```bash
rm ~/.tutr/config.json
```

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
