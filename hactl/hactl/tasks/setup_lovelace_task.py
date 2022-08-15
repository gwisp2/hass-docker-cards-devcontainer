import json
from pathlib import Path
from typing import List

import requests
from rich.markup import escape

from hactl.config import HactlConfig
from hactl.tasks.commons import TaskException

from .task import Task


class SetupLovelaceTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Setting up Lovelace")
        self.cfg = cfg

    def run(self) -> None:
        # Download Lovelace plugins
        workspace_path = self.cfg.paths.data / "www" / "workspace"
        workspace_path.mkdir(exist_ok=True, parents=True)

        # Download plugins from github
        downloaded_file_paths = self._download_plugins(
            self.cfg.lovelace.plugins, workspace_path
        )

        # Generate resources
        self._generate_resources_list(
            downloaded_file_paths, self.cfg.lovelace.extra_files, workspace_path
        )

    def _download_plugins(self, plugins: List[str], workspace_path: Path) -> List[Path]:
        js_module_paths: List[Path] = []

        n_failures = 0
        for plugin in plugins:
            author, repo = plugin.split("/")
            filename = repo.removeprefix("lovelace-")
            file_path = workspace_path / (filename + ".js")
            js_module_paths.append(file_path)

            if file_path.exists():
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
        self.log(f"Saving [blue]{escape(str(dest))}[/]")
        dest.write_bytes(content)

        return True

    def _generate_resources_list(
        self, js_module_paths: List[Path], extra_files: List[Path], workspace_path: Path
    ) -> None:
        # Generate configuration
        # Paths for downloaded plugins
        paths = [str(file.relative_to(workspace_path)) for file in js_module_paths]
        # Local paths
        paths.extend([str(Path("./local") / f) for f in extra_files])

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
        lovelace_config_file = self.cfg.paths.data / ".storage" / "lovelace_resources"
        lovelace_config_file.write_text(json.dumps(config), "utf-8")
