import os
import signal
import subprocess
import sys
import termios
from typing import Any, List, Literal, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape

from hactl.tasks import SetupLovelaceTask, TaskContextImpl

from .config import ConfigSource, DirConfigSource, FilesConfigSource, HactlConfig


class HaRunner:  # pylint: disable=too-few-public-methods
    Action = Literal["quit", "start", "reload_config"]

    def __init__(self, cfg_source: ConfigSource, console: Console) -> None:
        self.cfg_source = cfg_source
        self.console = console
        self.proc: Optional[subprocess.Popen[bytes]] = None
        self.old_terminal_state: Optional[List[Any]]
        self.cfg: Optional[HactlConfig] = None
        self._reload_config(verbose=False)

    def run(self) -> None:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        self._configure_stdin()

        if self.cfg is not None:
            self._run_hass()

        while True:
            next_action = self._prompt_next_action()
            if next_action == "quit":
                self._reset_terminal()
                return
            if next_action == "reload_config":
                self._reload_config()
            elif next_action == "start":
                self._run_hass()

    def _reload_config(self, verbose: bool = True) -> bool:
        try:
            self.cfg = self.cfg_source.load_config()
            if verbose:
                self.console.print("[green]Reloaded config[/]")
                self.console.print_json(self.cfg.json())

            # Recreate lovelace resources
            SetupLovelaceTask(self.cfg).execute(TaskContextImpl(self.console))

            return True
        except Exception as exc:  # pylint: disable=broad-except
            self.cfg = None
            self.console.print("[red]Invalid config[/red]")
            self.console.print(exc)
            return False

    def _prompt_next_action(self) -> Action:
        self.console.print(Markdown("# hactl"))
        if self.cfg is None:
            self.console.print("[yellow]Warning: no valid config[/]")
        if isinstance(self.cfg_source, DirConfigSource):
            # pylint: disable=line-too-long
            self.console.print(
                f"Config files: every file in {escape(str(self.cfg_source.configs_dir))}"  # noqa: E501
            )
        if isinstance(self.cfg_source, FilesConfigSource):
            self.console.print(
                f"Config files: {'; '.join([str(f) for f in self.cfg_source.files])}"
            )
        self.console.print("Press [blue]q[/] to exit")
        self.console.print("Press [blue]r[/] to reload config")
        if self.cfg is not None:
            self.console.print("Press [blue]s[/] to start HA")
        while True:
            key = sys.stdin.read(1)
            if key == "q":
                return "quit"
            if key == "s" and self.cfg is not None:
                return "start"
            if key == "r":
                return "reload_config"

    def _configure_stdin(self) -> None:
        """Makes possible to wait for a single key press"""

        self.old_terminal_state = termios.tcgetattr(sys.stdin)
        newattr = list(self.old_terminal_state)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(sys.stdin, termios.TCSANOW, newattr)

    def _reset_terminal(self) -> None:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)  # not sure if actually needed
        assert self.old_terminal_state is not None
        termios.tcsetattr(sys.stdin, termios.TCSANOW, self.old_terminal_state)

    def _run_hass(self) -> int:
        assert self.cfg is not None
        self.console.print(Markdown("# Home Assistant"))
        hass_path = self.cfg.paths.venv / "bin" / "hass"
        subprocess_env = dict(os.environ)
        subprocess_env.pop("PYTHONPATH", None)
        hass_command = [str(hass_path), "-c", str(self.cfg.paths.data), "-v"]

        # pylint: disable=consider-using-with
        self.proc = subprocess.Popen(
            hass_command,
            env=subprocess_env,
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=subprocess.STDOUT,
        )

        # HA has SIGINT handler also will be called on Ctrl+C
        # hactl process ignores SIGINT so we can wait for HA to exit
        return self.proc.wait()
