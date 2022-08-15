from rich.markup import escape

from ..config import HactlConfig
from .commons import run_command
from .task import Task


class InstallHaTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__(
            f"Installing HASS{' ' + escape(cfg.version) if cfg.version else ''}"
        )
        self.cfg = cfg

    def run(self) -> None:
        pip_path = self.cfg.paths.venv / "bin" / "pip"

        if not pip_path.exists():
            self.log(f"Creating virtualenv at {escape(str(self.cfg.paths.venv))}")
            run_command(["python", "-m", "venv", str(self.cfg.paths.venv)])

        run_command(
            [
                pip_path,
                "install",
                f"homeassistant{'==' + self.cfg.version if self.cfg.version else ''}",
                "sqlalchemy",
                "fnvhash",
            ]
        )
