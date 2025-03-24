#!/usr/bin/env python3
"""
GitHub repository sync script.
"""

import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from python_utilities.github_repos import main

if __name__ == "__main__":
    main()
