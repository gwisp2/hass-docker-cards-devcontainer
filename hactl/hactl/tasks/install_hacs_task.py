import zipfile
from io import BytesIO

import requests
from rich.markup import escape

from hactl.config import HactlConfig
from hactl.tasks.util.types import TaskException

from .task import Task


class InstallHacsTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Downloading HACS")
        self.cfg = cfg

    def run(self) -> None:
        hacs_dest_dir = self.cfg.ha.data / "custom_components" / "hacs"
        if hacs_dest_dir.exists():
            return

        hacs_fetch_url = (
            "https://github.com/hacs/integration/releases/latest/download/hacs.zip"
        )
        response = requests.get(hacs_fetch_url)
        if 200 <= response.status_code < 299:
            hacs_dest_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                zip_file.extractall(hacs_dest_dir)
        else:
            raise TaskException(
                f"HTTP {response.status_code} - {escape(hacs_fetch_url)}"
            )
