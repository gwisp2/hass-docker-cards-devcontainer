import hashlib
import re
from pathlib import Path
from typing import Optional

from git.remote import FetchInfo
from git.repo import Repo
from rich.markup import escape

from hactl.tasks.commons import run_command
from hactl.tasks.task import Task


class GitUtils:
    def __init__(self, task: Task) -> None:
        self.repos_dir = Path("~/.hactl/repos-bare").expanduser()
        self.worktrees_dir = Path("~/.hactl/repos-workdirs").expanduser()
        self.task = task

    def download_git_repository(self, source: str, force_fetch: bool = True) -> Repo:
        github_repo_match = re.fullmatch(r"([\w_-]+)/([\w_-]+)", source)
        if github_repo_match is not None:
            author = github_repo_match.group(1)
            reponame = github_repo_match.group(2)
            source = f"https://github.com/{author}/{reponame}.git"

        self.repos_dir.mkdir(parents=True, exist_ok=True)
        target_dir = self.repos_dir / hashlib.sha256(source.encode("utf-8")).hexdigest()

        repository = Repo.init(target_dir, bare=True)
        assert repository.bare

        is_new = False
        if len(repository.remotes) == 0:
            repository.create_remote("origin", source)
            is_new = True

        if is_new or force_fetch:
            self.task.log(f"Fetching {escape(source)}")
            fetch_results = repository.remotes[0].fetch()
            if any((r.flags & FetchInfo.HEAD_UPTODATE) == 0 for r in fetch_results):
                self.task.log("Something in the repository updated")
            else:
                self.task.log("Already up-to-date")

        return repository

    def get_repo_workdir(self, repository: Repo, ref: Optional[str] = None) -> Path:
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

    def get_from_git(
        self, location_with_optional_ref: str, force_fetch: bool = True
    ) -> Path:
        location_parts = location_with_optional_ref.split("#")
        ref = None
        if len(location_parts) >= 2:
            ref = location_parts[1]

        repository = self.download_git_repository(
            location_parts[0], force_fetch=force_fetch
        )
        return self.get_repo_workdir(repository, ref)
