import json
from pathlib import Path
from typing import List

import requests
from rich.markup import escape

from hactl.config import HactlConfig
from hactl.tasks.util.types import TaskException

from .task import Task


class SetupLovelaceTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Setting up Lovelace")
        self.cfg = cfg

    def run(self) -> None:
        # Download Lovelace plugins
        www_path = self.cfg.ha.data / "www"
        www_path.mkdir(exist_ok=True)

        # Download plugins from github
        plugin_github_repos = [
            p.github for p in self.cfg.lovelace if p.github is not None
        ]
        downloaded_file_paths = self._download_plugins(plugin_github_repos, www_path)

        # Get paths for local files
        local_plugin_paths = [p.path for p in self.cfg.lovelace if p.path is not None]

        # Generate resources
        self._generate_resources_list(
            [*downloaded_file_paths, *local_plugin_paths], www_path
        )

    def _download_plugins(self, plugins: List[str], www_path: Path) -> List[Path]:
        js_module_paths: List[Path] = []

        n_failures = 0
        for plugin in plugins:
            author, repo = plugin.split("/")
            filename = repo.removeprefix("lovelace-")
            file_path = www_path / (filename + ".js")
            js_module_paths.append(file_path)

            if file_path.exists():
                self.log(f"(exists) {escape(str(file_path))}")
                continue

            if not self._download_plugin(author, repo, filename, file_path):
                n_failures += 1

        if n_failures != 0:
            raise TaskException("Failed to load some plugins")

        return js_module_paths

    def _download_plugin(
        self, author: str, repo: str, filename: str, dest: Path
    ) -> bool:
        # Determine where to search for .js files
        # HEAD means the default branch
        # pylint: disable=line-too-long
        possible_download_urls = [
            f"https://raw.githubusercontent.com/{author}/{repo}/HEAD/{filename}.js",  # noqa: E501
            f"https://raw.githubusercontent.com/{author}/{repo}/HEAD/dist/{filename}.js",  # noqa: E501
            f"https://github.com/{author}/{repo}/releases/latest/download/{filename}.js",  # noqa: E501
            f"https://github.com/{author}/{repo}/releases/latest/download/{filename}-bundle.js",  # noqa: E501
        ]

        # Find file by examining every url
        content = None
        response_status_codes: List[int] = []
        for possible_url in possible_download_urls:
            response = requests.get(possible_url)
            if 200 <= response.status_code <= 299:
                content = response.content
                break
            response_status_codes.append(response.status_code)

        # All urls failed
        if content is None:
            self.log(
                f"[red]Failed to download [blue]{escape(author + '/' + repo)}[/][/]"
            )
            for download_url, code in zip(
                possible_download_urls, response_status_codes
            ):
                self.log(f"[red]HTTP {code} - [blue]{download_url}[/blue]")
            return False

        # Save downloaded file
        self.log(f"[yellow](downloaded)[/] {escape(str(dest))}")
        dest.write_bytes(content)

        return True

    def _generate_resources_list(self, paths: List[Path], www_path: Path) -> None:
        # Make paths relative
        paths = [Path("local") / file.relative_to(www_path) for file in paths]

        # Generate configuration
        self.log(f"{len(paths)} module(s) for Lovelace found")
        config = {
            "data": {
                "items": [
                    {"id": f"{i}", "type": "module", "url": f"{p}"}
                    for i, p in enumerate(paths)
                ]
            },
            "key": "lovelace_resources",
            "version": 1,
        }

        # Save configuration
        lovelace_config_file = self.cfg.ha.data / ".storage" / "lovelace_resources"
        lovelace_config_file.write_text(json.dumps(config), "utf-8")
