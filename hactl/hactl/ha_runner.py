import contextlib
import os
import signal
import subprocess
import sys
import termios
from datetime import datetime, timedelta
from multiprocessing import Pipe
from selectors import EVENT_READ, DefaultSelector
from types import FrameType
from typing import Any, Generator, List, Literal, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape

from hactl.tasks import SetupLovelaceTask, TaskContextImpl

from .config import ConfigSource, DirConfigSource, FilesConfigSource, HactlConfig
from .tasks.commons import FileDescriptorLike, LineTracker, make_nonblocking


class HaRunner:  # pylint: disable=too-few-public-methods
    Action = Literal["quit", "start", "reload_config"]

    def __init__(self, cfg_source: ConfigSource, console: Console) -> None:
        self.cfg_source = cfg_source
        self.console = console
        self.old_terminal_state: Optional[List[Any]]
        self.cfg: Optional[HactlConfig] = None
        self.sigint_tracker = SigintTracker()

        self._reload_config(verbose=False)

    def run(self) -> None:
        signal.signal(signal.SIGINT, self.sigint_tracker.handle_sigint)
        self._configure_stdin()

        try:
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
        finally:
            # Restore old terminal settings
            self._reset_terminal()

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

    def _run_hass(self) -> None:
        self.console.print(Markdown("# Home Assistant"))

        # Forget old interrupts
        self.sigint_tracker.reset()

        # Start HASS (also waits for HA on exit)
        with self._start_hass() as proc:
            # Get stdout of HA
            out = proc.stdout
            assert out is not None

            # Loop and print HA logs
            with DefaultSelector() as selector:
                selector.register(out, EVENT_READ)
                selector.register(self.sigint_tracker.fd_for_wait(), EVENT_READ)

                # Read & log lines
                line_tracker = LineTracker()
                while True:
                    events = selector.select()
                    ha_events = next(
                        (f_events for key, f_events in events if key.fileobj == out), 0
                    )

                    if self.sigint_tracker.had_sigints():
                        streak_length_to_kill = 5
                        streak = self.sigint_tracker.streak()
                        if streak < streak_length_to_kill:
                            self.console.print(
                                "[yellow]Sent SIGINT to Home Assistant, press Ctrl+C"
                                f" {streak_length_to_kill - streak}"
                                " times more to kill[/]"
                            )
                            proc.send_signal(signal.SIGINT)
                        else:
                            self.console.print("[yellow]:skull: Killing HA[/]")
                            proc.kill()

                    if ha_events & EVENT_READ:
                        data = out.read()
                        for line in line_tracker.lines(data):
                            self._print_ha_log_line(line)
                        if len(data) == 0:
                            # EOF - most likely HA stopped
                            break

    def _print_ha_log_line(self, line: bytes) -> None:
        assert self.cfg is not None
        line_str = line.decode("utf-8", errors="replace")
        line_color = self.cfg.logging.color_for_line(line_str) or "grey50"
        self.console.print(f"[{line_color}]{escape(line_str)}[/]")

    @contextlib.contextmanager
    def _start_hass(self) -> Generator[subprocess.Popen[bytes], None, None]:
        assert self.cfg is not None

        # Important: use python -m homeassistant.__main__ instead of running bin/hass
        # debugpy can't understand to inject into the subprocess in the latter case
        python_path = self.cfg.paths.venv / "bin" / "python"
        subprocess_env = dict(os.environ)
        subprocess_env.pop("PYTHONPATH", None)
        hass_command = [
            str(python_path),
            "-m",
            "homeassistant.__main__",
            "-c",
            str(self.cfg.paths.data),
            "-v",
        ]

        with subprocess.Popen(
            hass_command,
            env=subprocess_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # detach from terminal so that Ctrl+C is not propagated
            start_new_session=True,
        ) as proc:
            try:
                assert proc.stdout is not None
                make_nonblocking(proc.stdout)
                yield proc
            except Exception:
                self.console.print("[red]something went wrong[/]")
                self.console.print_exception()
                proc.kill()
                raise


class SigintTracker:
    def __init__(self, streak_max_delay: timedelta = timedelta(seconds=3)) -> None:
        self._streak = 0
        self._last_sigint_dt: Optional[datetime] = None
        self._r, self._w = Pipe(False)
        self._streak_max_delay = streak_max_delay
        make_nonblocking(self._r)
        make_nonblocking(self._w)

    def reset(self) -> None:
        while self._r.poll():
            self._r.recv_bytes()
        self._streak = 0
        self._last_sigint_dt = None

    def handle_sigint(self, _sig: int, _frame_type: Optional[FrameType]) -> None:
        now = datetime.now()
        if (
            self._last_sigint_dt is None
            or now - self._last_sigint_dt <= self._streak_max_delay
        ):
            self._streak += 1
        else:
            self._streak = 1
        self._last_sigint_dt = now
        try:
            self._w.send_bytes(b"s")
        except BlockingIOError:
            # ignore
            pass

    def fd_for_wait(self) -> FileDescriptorLike:
        return self._r

    def streak(self) -> int:
        return self._streak

    def had_sigints(self) -> bool:
        """Checks if sigints were received since last had_sigints call"""
        if not self._r.poll():
            return False
        while self._r.poll():
            self._r.recv_bytes()
        return True
