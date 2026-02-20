# tmht — Tell Me How To

AI-powered terminal assistant that generates commands from natural language.

```
$ tmht git create and switch to a new branch called testing

  git checkout -b testing
```

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/spi/tmht.git
cd tmht
uv sync
```

## Setup

On first run, tmht launches an interactive setup to select your provider, model, and API key:

```
$ tmht git "show recent commits"

Welcome to tmht! Let's get you set up.

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

Configuration saved to ~/.tmht/config.json
```

Setup is skipped if `~/.tmht/config.json` already exists or provider API key environment variables are set.

## Usage

```
tmht <command> <what you want to do>
```

### Examples

```bash
tmht git "create and switch to a new branch called testing"
tmht sed "replace all instances of 'foo' with 'bar' in myfile.txt"
tmht curl "http://example.com and display all request headers"
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

## Configuration

Config is stored in `~/.tmht/config.json`. Environment variables override the config file.

| Environment Variable | Description | Default |
|---|---|---|
| `TMHT_MODEL` | LLM model to use ([litellm format](https://docs.litellm.ai/docs/providers)) | `gemini/gemini-3-flash-preview` |
| `GEMINI_API_KEY` | Gemini API key | — |
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |

To re-run setup, delete the config file:

```bash
rm ~/.tmht/config.json
```
