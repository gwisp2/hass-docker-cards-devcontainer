from rich.markup import escape

from hactl.tasks.util.commands import run_command

from ..config import HactlConfig
from .task import Task


class InstallHaTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Installing homeassistant")
        self.cfg = cfg
        self.version_constrant: str = ""
        if self.cfg.ha.version is not None:
            self.version_constrant = "==" + self.cfg.ha.version

    def run(self) -> None:
        pip_path = self.cfg.ha.venv / "bin" / "pip"

        if not pip_path.exists():
            self.log(f"Creating virtualenv at {escape(str(self.cfg.ha.venv))}")
            run_command(["python", "-m", "venv", str(self.cfg.ha.venv)])

        run_command(
            [
                pip_path,
                "install",
                f"homeassistant{self.version_constrant}",
                "sqlalchemy",
                "fnvhash",
            ]
        )
