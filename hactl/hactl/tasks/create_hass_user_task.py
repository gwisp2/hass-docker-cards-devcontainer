from rich.markup import escape

from hactl.config import HactlConfig
from hactl.tasks.util.commands import run_hass_command

from .task import Task


class CreateHassUserTask(Task):
    cfg: HactlConfig

    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__(f"Creating user [blue]{escape(cfg.ha.user.name)}[/]")
        self.cfg = cfg

    def run(self) -> None:
        username = self.cfg.ha.user.name
        password = self.cfg.ha.user.password

        run_hass_command(
            venv=self.cfg.ha.venv,
            args=["add", username, password],
            data_path=self.cfg.ha.data,
            script_name="auth",
        )
