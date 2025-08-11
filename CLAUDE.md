# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python tool called "youtrack-catchup" that helps users quickly catch up on YouTrack issues requiring their attention. It aims to provide actionable items rather than the noisy default email notifications.

## Technology Stack

- **Python**: 3.13+ required
- **Package Manager**: Poetry
- **Key Dependencies**:
  - `python-dotenv`: Environment variable management
  - `openai`: OpenAI API integration
  - `requests`: HTTP client

## Project Structure

```
youtrack-catchup/
├── src/
│   └── youtrack_catchup/     # Main package source code
├── tests/                     # Test directory (currently empty)
├── pyproject.toml            # Poetry configuration and dependencies
└── .env.template             # Environment variables template
```

## Development Setup

### Environment Configuration

Copy `.env.template` to `.env` and configure:
- `YOUTRACK_URL`: Your YouTrack instance URL
- `YOUTRACK_TOKEN`: YouTrack API token
- `OPEN_AI_TOKEN`: OpenAI API key

### Common Commands

```bash
# Install dependencies
poetry install

# Run the application
poetry run python -m youtrack_catchup

# Add a new dependency
poetry add <package-name>

# Add a development dependency
poetry add --group dev <package-name>

# Update dependencies
poetry update

# Build the package
poetry build

# Format the code
poetry run ruff
```

## Testing

The project has a `tests/` directory structure set up but no tests implemented yet. When adding tests:
```bash
# Run tests (once implemented)
poetry run pytest

# Run a specific test file
poetry run pytest tests/test_<module>.py

# Run tests with coverage
poetry run pytest --cov=youtrack_catchup
```

## Architecture Notes

- The project uses Poetry for dependency management and packaging
- Configuration is managed through environment variables loaded via python-dotenv
- The main package is located in `src/youtrack_catchup/`
- The project integrates with YouTrack API and OpenAI API for processing issues
