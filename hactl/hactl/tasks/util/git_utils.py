import hashlib
import re
from pathlib import Path
from typing import Optional

from git.repo import Repo
from rich.markup import escape

from hactl.tasks.task import Task
from hactl.tasks.util.commands import run_command


class GitUtils:
    def __init__(self, task: Task) -> None:
        self.repos_dir = Path("~/.hactl/repos-bare").expanduser()
        self.worktrees_dir = Path("~/.hactl/repos-worktrees").expanduser()
        self.task = task

    def _prepare_source_url(self, source_url: str) -> str:
        github_repo_match = re.fullmatch(r"([\w_-]+)/([\w_-]+)", source_url)
        if github_repo_match is not None:
            author = github_repo_match.group(1)
            reponame = github_repo_match.group(2)
            source = f"https://github.com/{author}/{reponame}.git"
        else:
            source = source_url
        return source

    def _get_repository_dir(self, source: str) -> Path:
        source = self._prepare_source_url(source)
        return self.repos_dir / hashlib.sha256(source.encode("utf-8")).hexdigest()

    def download_git_repository(self, source: str, force_fetch: bool = True) -> Repo:
        self.repos_dir.mkdir(parents=True, exist_ok=True)

        source = self._prepare_source_url(source)
        target_dir = self._get_repository_dir(source)
        repository = Repo.init(target_dir, bare=True)
        assert repository.bare

        is_new = False
        if len(repository.remotes) == 0:
            repository.create_remote("origin", source)
            is_new = True

        if is_new or force_fetch:
            self.task.log(f"Fetching {escape(source)}")
            repository.remotes[0].fetch()

        return repository

    def get_repo_worktree(self, repository: Repo, ref: Optional[str] = None) -> Path:
        if ref is None:
            # find default branch
            ref = repository.head.ref.path.split("/")[-1]

        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        workdir_name = hashlib.sha256(
            (repository.remotes[0].url + "#" + ref).encode("utf-8")
        ).hexdigest()
        workdir_path = self.worktrees_dir / workdir_name

        if not workdir_path.exists():
            run_command(
                ["git", "worktree", "add", workdir_path, ref], cwd=repository.common_dir
            )
        run_command(["git", "checkout", ref], cwd=workdir_path)

        return workdir_path

    def get_current_commit_sha(self, worktree: Path) -> str:
        repo = Repo(worktree)
        return repo.commit().hexsha

    def get_from_git(
        self, location_with_optional_ref: str, force_fetch: bool = True
    ) -> Path:
        location_parts = location_with_optional_ref.split("#")
        ref = None
        if len(location_parts) >= 2:
            ref = location_parts[1]
        repo_source = location_parts[0]

        # Remember previous state
        repo_dir = self._get_repository_dir(repo_source)
        prev_commit_sha: Optional[str] = None
        if repo_dir.exists():
            prev_commit_sha = self.get_current_commit_sha(
                self.get_repo_worktree(Repo(repo_dir))
            )

        # Update repositories
        repository = self.download_git_repository(repo_source, force_fetch=force_fetch)
        new_worktree = self.get_repo_worktree(repository, ref)

        # Compare commits
        new_commit_sha = self.get_current_commit_sha(new_worktree)
        if new_commit_sha != prev_commit_sha:
            self.task.log(f"Updated from {prev_commit_sha} to {new_commit_sha}")
        else:
            self.task.log("Already up-to-date")

        return new_worktree
