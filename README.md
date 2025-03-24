# Python Utilities

A collection of Python utilities for various tasks.

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
- `--log-file`: Path to log file (default: github_sync.log)

#### Example
```bash
# First time setup with token storage
python -m python_utilities.scripts.github_sync myusername --token mytoken --store-token

# Subsequent runs (token will be retrieved from keyring)
python -m python_utilities.scripts.github_sync myusername
```

## Development

### Setup
1. Clone the repository
2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

### Running Tests
```bash
pytest
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