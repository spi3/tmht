# Vision

This file outlines the vision for the project.

## Overview

tutr (Terminal Utility for con(T)extual Responses) is an AI powered terminal assistant which assists users in discovering and executing terminal commands.

## Terminal

The `tutr` tool is meant to be run from the terminal command line as a quick, one shot, command which will produce a terminal command based on prompt.

### Invoking

The `tutr` tool will be invoked in the terminal via the `tutr` command.

Examples:
    - `> tutr git create and switch to new branch called 'testing'`
    - `> tutr sed replace all instances of 'something' with 'something else' in ~/some_file.txt`
    - `> tutr curl http://somewebsite.com and display all request headers`

## AI Power

At its core `tutr` compiles a simple set of context, invokes an LLM, and returns a response to the user directly in the terminal.

## Context

When invoked `tutr` will receive a few key pieces of context:

1. The command being investigated (if known).
Ex: 
    -`git`
    - `sed`
    - Any terminal command installed in the system

2. Documentation regarding the tool:
Ex:
    - Man page for the command. Generated with `man $CMD`
    - Help argument for the command. Generated with `$CMD --help`
    - Other documentation sources

## Interactive Shell Wrapper

In addition to one-shot queries, `tutr` can operate as an interactive shell wrapper. When launched
as a wrapper, `tutr` runs a PTY session around the user's normal shell. After any command exits
with a non-zero status, `tutr` captures recent terminal output and automatically generates a
contextual suggestion for what the user may have meant to do, without requiring a separate
`tutr <query>` invocation.

The wrapped shell inherits the user's full environment and sources their rc file. A prompt prefix
(default `[tutr]`) indicates the wrapper is active, and the `TUTR_ACTIVE=1` environment variable
is set so scripts and other tools can detect the wrapped context.

### Shell Auto-start

Users can configure their shell rc file to launch the wrapper automatically for every new
interactive terminal session. A recursion guard (`TUTR_AUTOSTARTED`) prevents the wrapper shell
from re-launching itself when it sources the rc file.

### Shell Detection

The wrapper detects the user's preferred shell automatically and supports Bash, Zsh, and
PowerShell. The `TUTR_SHELL` environment variable can override detection for non-standard setups.
