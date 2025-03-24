"""
GitHub repository management utilities.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional
import requests
from requests.auth import HTTPBasicAuth


class GitHubRepoManager:
    def __init__(
        self,
        username: str,
        token: Optional[str] = None,
        base_path: str = "/volume1/archive/github-repos",
    ):
        """
        Initialize the GitHub repository manager.

        Args:
            username: GitHub username
            token: GitHub personal access token (optional)
            base_path: Base path for storing repositories
        """
        self.username = username
        self.token = token
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        if token:
            self.session.auth = HTTPBasicAuth(username, token)

    def get_repos(self) -> List[dict]:
        """
        Fetch all repositories for the user.

        Returns:
            List of repository information dictionaries
        """
        repos = []
        page = 1
        while True:
            response = self.session.get(
                f"https://api.github.com/users/{self.username}/repos",
                params={"page": page, "per_page": 100},
            )
            response.raise_for_status()
            page_repos = response.json()
            if not page_repos:
                break
            repos.extend(page_repos)
            page += 1
        return repos

    def clone_or_update_repo(self, repo: dict) -> None:
        """
        Clone a repository if it doesn't exist, or update it if it does.

        Args:
            repo: Repository information dictionary
        """
        repo_name = repo["name"]
        repo_path = self.base_path / repo_name
        repo_url = repo["clone_url"]

        if not repo_path.exists():
            print(f"Cloning {repo_name}...")
            subprocess.run(["git", "clone", repo_url, str(repo_path)], check=True)
        else:
            print(f"Updating {repo_name}...")
            subprocess.run(
                ["git", "-C", str(repo_path), "pull", "--rebase"],
                check=True,
            )

    def sync_all_repos(self) -> None:
        """
        Synchronize all repositories.
        """
        try:
            repos = self.get_repos()
            for repo in repos:
                try:
                    self.clone_or_update_repo(repo)
                except subprocess.CalledProcessError as e:
                    print(f"Error processing {repo['name']}: {e}")
                except Exception as e:
                    print(f"Unexpected error processing {repo['name']}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repositories: {e}")


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync GitHub repositories")
    parser.add_argument("username", help="GitHub username")
    parser.add_argument(
        "--token",
        help="GitHub personal access token (optional)",
        default=os.environ.get("GITHUB_TOKEN"),
    )
    parser.add_argument(
        "--base-path",
        help="Base path for storing repositories",
        default="/volume1/archive/github-repos",
    )

    args = parser.parse_args()

    manager = GitHubRepoManager(
        username=args.username,
        token=args.token,
        base_path=args.base_path,
    )
    manager.sync_all_repos()


if __name__ == "__main__":
    main() 