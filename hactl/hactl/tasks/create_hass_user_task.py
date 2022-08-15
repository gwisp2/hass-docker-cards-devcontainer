from rich.markup import escape

from hactl.config import HactlConfig
from hactl.tasks.commons import run_hass_command

from .task import Task


class CreateHassUserTask(Task):
    cfg: HactlConfig

    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__(f"Creating user [blue]{escape('dev')}[/]")
        self.cfg = cfg

    def run(self) -> None:
        username = self.cfg.user.name
        password = self.cfg.user.password

        run_hass_command(
            venv=self.cfg.paths.venv,
            args=["--script", "auth", "add", username, password],
            data_path=self.cfg.paths.data,
        )
