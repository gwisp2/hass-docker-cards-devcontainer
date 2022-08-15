from hactl.config import HactlConfig
from hactl.tasks.commons import run_hass_command
from hactl.tasks.task import Task


class EnsureHassConfigExistsTask(Task):
    cfg: HactlConfig

    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Ensuring Home Assistant configuration exists")
        self.cfg = cfg

    def run(self) -> None:
        run_hass_command(
            venv=self.cfg.paths.venv,
            args=[
                "--script",
                "ensure_config",
            ],
            data_path=self.cfg.paths.data,
        )
