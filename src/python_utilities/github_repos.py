"""
GitHub repository management utilities.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import keyring
import requests
from requests.auth import HTTPBasicAuth
from tqdm import tqdm


class Logger:
    """
    A logger class that handles structured logging in JSON format suitable for ELK stack.
    
    This logger tracks various statistics about repository operations and writes
    detailed logs and summaries to a specified file. Each log entry includes a
    timestamp, event type, message, and any additional fields provided.
    
    Attributes:
        log_file (Path): Path to the log file where entries will be written
        start_time (float): Timestamp when the logger was initialized
        stats (Dict[str, int]): Dictionary tracking counts of various operations
    """

    def __init__(self, log_file: str) -> None:
        """
        Initialize the logger.
        
        Args:
            log_file: Path to the log file where entries will be written
        """
        self.log_file = Path(log_file)
        # Create parent directories if they don't exist
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.start_time = time.time()
        self.stats: Dict[str, int] = {
            "cloned": 0,
            "updated": 0,
            "moved": 0,
            "deleted": 0,
            "errors": 0
        }
       
    def log(self, event_type: str, message: str, **kwargs: Any) -> None:
        """
        Log an event in JSON format suitable for ELK stack.
        
        Args:
            event_type: Type of event (detail or summary)
            message: Human readable message
            **kwargs: Additional fields to include in the log
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "message": message,
            **kwargs
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
   
    def increment_stat(self, stat: str) -> None:
        """Increment a statistic counter."""
        if stat in self.stats:
            self.stats[stat] += 1
   
    def log_summary(self) -> None:
        """Log a summary of the sync operation."""
        duration = time.time() - self.start_time
        self.log(
            "summary",
            "GitHub repository sync completed",
            duration_seconds=duration,
            stats=self.stats
        )


class GitHubRepoManager:
    """
    A manager class for synchronizing GitHub repositories.
    
    This class handles all operations related to GitHub repositories including:
    - Fetching repository information from GitHub API
    - Cloning new repositories
    - Updating existing repositories
    - Deleting repositories that no longer exist remotely
    - Moving repositories between public/private folders based on visibility changes
    
    The manager maintains a structured log of all operations and provides
    progress feedback during synchronization.
    
    Attributes:
        username (str): GitHub username for authentication
        token (str): GitHub personal access token for API access
        base_path (Path): Base directory for storing repositories
        logger (Logger): Logger instance for tracking operations
        session (requests.Session): Session for making GitHub API requests
    """
    
    def __init__(
        self,
        username: str,
        token: Optional[str] = None,
        base_path: str = "/Volumes/archive/github-repos",
        log_file: str = "github_sync.log",
    ) -> None:
        """
        Initialize the GitHub repository manager.

        Args:
            username: GitHub username
            token: GitHub personal access token (optional)
            base_path: Base path for storing repositories
            log_file: Path to log file

        Raises:
            RuntimeError: If the base path is not accessible or cannot be created
        """
        self.username = username
        self.token = token or keyring.get_password("github_repos", username)
        self.base_path = Path(base_path)
        self.logger = Logger(log_file)
        
        # Check if the base path is accessible
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            if e.errno == 30:  # Read-only file system
                raise RuntimeError(
                    "Cannot access {base_path}. Please ensure the Synology NAS is "
                    "mounted and you have write permissions."
                ) from e
            raise RuntimeError(
                "Cannot create directory {base_path}. Please check if the path "
                "exists and you have write permissions."
            ) from e
            
        self.session = requests.Session()
        if self.token:
            self.session.auth = HTTPBasicAuth(username, self.token)

    def get_repos(self) -> List[Dict[str, Any]]:
        """
        Fetch all repositories for the user (both public and private).

        Returns:
            List of repository information dictionaries

        Raises:
            RuntimeError: If authentication fails or repository fetch fails
        """
        repos = []
        page = 1
        while True:
            try:
                response = self.session.get(
                    "https://api.github.com/user/repos",
                    params={"page": page, "per_page": 100},
                )
                response.raise_for_status()
                page_repos = response.json()
                if not page_repos:
                    break
                repos.extend(page_repos)
                page += 1
            except requests.exceptions.RequestException as e:
                if response.status_code == 401:
                    raise RuntimeError(
                        "Authentication failed. Please check your GitHub token."
                    ) from e
                raise RuntimeError(
                    f"Failed to fetch repositories: {e}"
                ) from e
        return repos

    def clone_or_update_repo(self, repo: Dict[str, Any]) -> None:
        """
        Clone a repository if it doesn't exist, or update it if it does.

        Args:
            repo: Repository information dictionary

        Raises:
            RuntimeError: If cloning or updating fails
        """
        repo_name = repo["name"]
        # Create public or private subfolder based on repository visibility
        visibility_folder = "private" if repo["private"] else "public"
        repo_path = self.base_path / visibility_folder / repo_name
        repo_url = repo["clone_url"]

        try:
            if not repo_path.exists():
                self.logger.log(
                    "detail",
                    f"Cloning repository {repo_name}",
                    action="clone",
                    repo_name=repo_name,
                    visibility=visibility_folder
                )
                subprocess.run(["git", "clone", repo_url, str(repo_path)], check=True)
                self.logger.increment_stat("cloned")
            else:
                self.logger.log(
                    "detail",
                    f"Updating repository {repo_name}",
                    action="update",
                    repo_name=repo_name,
                    visibility=visibility_folder
                )
                subprocess.run(
                    ["git", "-C", str(repo_path), "pull", "--rebase"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.logger.increment_stat("updated")
        except subprocess.CalledProcessError as e:
            action = "clone" if not repo_path.exists() else "update"
            error_msg = f"Failed to {action} repository {repo_name}: {e}"
            self.logger.log(
                "detail",
                error_msg,
                action="error",
                repo_name=repo_name,
                visibility=visibility_folder,
                error=str(e)
            )
            self.logger.increment_stat("errors")
            raise RuntimeError(error_msg) from e

    def sync_all_repos(self) -> None:
        """
        Synchronize all repositories.
        - Clones new repositories
        - Updates existing repositories
        - Deletes repositories that no longer exist remotely
        - Moves repositories between public/private folders if visibility changed

        Raises:
            RuntimeError: If any operation fails
        """
        self.logger.log("detail", "Starting GitHub repository synchronization")
        
        # Get remote repositories
        try:
            remote_repos = self.get_repos()
            self.logger.log(
                "detail",
                f"Found {len(remote_repos)} repositories on GitHub",
                total_repos=len(remote_repos)
            )
        except RuntimeError as e:
            self.logger.log(
                "detail",
                "Failed to fetch repositories from GitHub",
                error=str(e)
            )
            raise

        # Create sets for efficient lookup
        remote_repo_names = {repo["name"] for repo in remote_repos}
        remote_repo_visibility = {
            repo["name"]: "private" if repo["private"] else "public"
            for repo in remote_repos
        }

        # Process each repository
        for repo in tqdm(remote_repos, desc="Processing repositories"):
            try:
                self.clone_or_update_repo(repo)
            except RuntimeError as e:
                self.logger.log(
                    "detail",
                    f"Failed to process repository {repo['name']}",
                    error=str(e)
                )
                continue

        # Check for repositories that need to be moved or deleted
        for visibility in ["public", "private"]:
            folder_path = self.base_path / visibility
            if not folder_path.exists():
                continue

            for repo_path in folder_path.iterdir():
                if not repo_path.is_dir():
                    continue

                repo_name = repo_path.name
                if repo_name not in remote_repo_names:
                    # Repository no longer exists on GitHub
                    try:
                        self.logger.log(
                            "detail",
                            f"Deleting repository {repo_name} (no longer exists on GitHub)",
                            action="delete",
                            repo_name=repo_name,
                            visibility=visibility
                        )
                        shutil.rmtree(repo_path)
                        self.logger.increment_stat("deleted")
                    except OSError as e:
                        self.logger.log(
                            "detail",
                            f"Failed to delete repository {repo_name}",
                            error=str(e)
                        )
                        self.logger.increment_stat("errors")
                elif remote_repo_visibility[repo_name] != visibility:
                    # Repository visibility has changed
                    try:
                        new_path = self.base_path / remote_repo_visibility[repo_name] / repo_name
                        self.logger.log(
                            "detail",
                            f"Moving repository {repo_name} from {visibility} to {remote_repo_visibility[repo_name]}",
                            action="move",
                            repo_name=repo_name,
                            from_visibility=visibility,
                            to_visibility=remote_repo_visibility[repo_name]
                        )
                        shutil.move(str(repo_path), str(new_path))
                        self.logger.increment_stat("moved")
                    except OSError as e:
                        self.logger.log(
                            "detail",
                            f"Failed to move repository {repo_name}",
                            error=str(e)
                        )
                        self.logger.increment_stat("errors")

        # Log summary
        self.logger.log_summary()


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Sync GitHub repositories")
    parser.add_argument("username", help="GitHub username")
    parser.add_argument(
        "--token",
        help=(
            "GitHub personal access token (optional). If not provided, "
            "will try to get from keyring."
        ),
        default=os.environ.get("GITHUB_TOKEN"),
    )
    parser.add_argument(
        "--store-token",
        help="Store the provided token in the system keyring",
        action="store_true",
    )
    parser.add_argument(
        "--base-path",
        help="Base path for storing repositories",
        default="/Volumes/archive/github-repos",
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file (default: github_sync.log in current directory)",
        default="github_sync.log",
    )

    args = parser.parse_args()

    try:
        # Store token if explicitly requested or if token is provided and not already stored
        if args.token:
            stored_token = keyring.get_password("github_repos", args.username)
            if args.store_token or not stored_token:
                keyring.set_password("github_repos", args.username, args.token)
                print(f"Token stored in keyring for user {args.username}")
                if not args.store_token:
                    print("Note: Token was automatically stored for future use")

        manager = GitHubRepoManager(
            username=args.username,
            token=args.token,
            base_path=args.base_path,
            log_file=args.log_file,
        )
        manager.sync_all_repos()
    except (RuntimeError, requests.exceptions.RequestException, subprocess.CalledProcessError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 