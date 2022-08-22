from hactl.config import HactlConfig
from hactl.tasks.task import Task
from hactl.tasks.util.commands import run_hass_command


class EnsureHassConfigExistsTask(Task):
    cfg: HactlConfig

    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Ensuring Home Assistant configuration exists")
        self.cfg = cfg

    def run(self) -> None:
        run_hass_command(
            venv=self.cfg.paths.venv,
            args=[],
            data_path=self.cfg.paths.data,
            script_name="ensure_config",
        )
