# Python Utilities

A collection of Python utilities for various tasks, developed with assistance from AI agents in Cursor IDE. These scripts are designed to automate common development and system administration tasks, with a focus on code quality, maintainability, and user experience.

## Project Structure

```
python-utilities/
├── src/
│   └── python_utilities/
│       ├── scripts/           # Command-line scripts
│       │   └── github_sync.py # GitHub repository sync script
│       └── __init__.py        # Package initialization
├── tests/                     # Test files
├── pyproject.toml            # Project configuration and dependencies
├── uv.lock                   # Locked dependency versions
└── README.md                 # This file
```

## Available Scripts

### GitHub Repository Sync (`github_sync.py`)

A script to synchronize GitHub repositories locally, organizing them into public and private folders.

#### Features
- Clones new repositories
- Updates existing repositories
- Deletes repositories that no longer exist remotely
- Moves repositories between public/private folders based on visibility changes
- Provides progress feedback with a progress bar
- Logs operations in JSON format suitable for ELK stack
- Securely stores GitHub token in system keyring

#### Usage
```bash
# Basic usage
python -m python_utilities.scripts.github_sync <username>

# With options
python -m python_utilities.scripts.github_sync <username> \
    --token <github_token> \
    --store-token \
    --base-path /path/to/repos \
    --log-file sync.log
```

#### Options
- `username`: GitHub username (required)
- `--token`: GitHub personal access token (optional, defaults to environment variable GITHUB_TOKEN)
- `--store-token`: Store the provided token in system keyring
- `--base-path`: Base directory for storing repositories (default: /Volumes/archive/github-repos)
- `--log-file`: Path to log file (default: github_sync.log in current directory)

#### Example
```bash
# First time setup with token storage (replace YOUR_GITHUB_TOKEN with your actual token)
python -m python_utilities.scripts.github_sync myusername --token YOUR_GITHUB_TOKEN --store-token

# Subsequent runs (token will be retrieved from keyring)
python -m python_utilities.scripts.github_sync myusername
```

## Development

### Setup
1. Clone the repository
2. Install dependencies using `uv`:
   ```bash
   # Install all dependencies including development tools
   uv sync --extras dev
   ```

### Running Tests
```bash
pytest
```

### Code Quality
The project uses `ruff` for linting and code formatting. To run the linter:
```bash
ruff check .
```

To automatically fix issues that can be fixed:
```bash
ruff check --fix .
```

### Pre-commit Hooks
This project uses pre-commit hooks to ensure code quality and security. The hooks include:
- Security scanning with `bandit`
- Code formatting with `ruff`
- Various file checks (trailing whitespace, merge conflicts, etc.)
- Private key detection

To set up pre-commit hooks:
```bash
# Install pre-commit
uv pip install pre-commit

# Install the git hooks
pre-commit install

# Run against all files (optional)
pre-commit run --all-files
```

The hooks will run automatically on each commit, but you can also run them manually:
```bash
pre-commit run --all-files
```

### Adding New Scripts
1. Create a new Python file in `src/python_utilities/scripts/`
2. Add command-line argument parsing using `argparse`
3. Add the script to the project structure section in this README
4. Add tests in the `tests/` directory

## Installation

This project uses `uv` as the package manager. To install:

```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
uv pip install -e .
```

## License

MIT License 