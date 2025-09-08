# Issue-Fixer

Automated GitHub issue resolver that uses Claude AI to analyze and fix issues in repositories.

## Overview

Issue-Fixer is a Python tool that:
1. Fetches open issues from a GitHub repository
2. Uses Claude 3.7 Sonnet or 3.5 Haiku to analyze the codebase
3. Implements fixes for the issues
4. Creates branches with commits containing the fixes
5. Prepares everything for pull request creation

## Features

- Automated GitHub issue parsing
- Intelligent code analysis using Claude
- Automatic code modification and fixes
- Git branch management and commit creation
- Support for multiple Claude models (Haiku, Sonnet)

## Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (for package management)
- GitHub access token with repo permissions
- Anthropic API key

## Installation

1. Clone this repository
2. Install dependencies using uv:
```
uv sync --frozen
```

## Configuration
Create a `.env` file with the following variables:
```
GITHUB_TOKEN=your_github_token
ANTHROPIC_API_KEY=your_api_key
```

## Usage
1. Run the main script to process all open issues:
```
uv run main.py
```

2. Review fixes and merge if satisfactory

## Tools

Claude is provided with several tools to interact with the codebase:

- `find_code_patterns`: Search for specific patterns in code
- `read_code_snippet`: View code around matched lines
- `read_file`: Read entire files
- `edit_file`: Make changes to files

## Project Structure

- `main.py`: Main script for issue processing
- `tools.py`: Tools for code analysis/modification
- `.env`: Environment variables for configuration
- `cloned_repo/`: Directory where target repos are cloned