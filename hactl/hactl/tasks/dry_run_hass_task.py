import os
import subprocess
import tempfile
from io import BytesIO
from selectors import EVENT_READ, DefaultSelector
from signal import SIGINT
from typing import IO, Dict, Literal, Optional, Tuple

from rich.padding import Padding

from hactl.config import HactlConfig
from hactl.tasks.util.commands import LineTracker, make_nonblocking
from hactl.tasks.util.types import TaskException

from .task import Task


class DryRunHassTask(Task):
    LineWaitResult = Literal["timeout", "crash", "ok"]

    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Running Home Assistant to install missing packages")
        self.cfg = cfg

    def run(self) -> None:
        hass_path = self.cfg.ha.venv / "bin" / "hass"

        # Forbid using non-virtualenv packages
        subprocess_env = dict(os.environ)
        subprocess_env.pop("PYTHONPATH", None)

        # Run HA in a temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Start HA
            hass_command = [str(hass_path), "-c", str(tmp_dir), "-v"]

            # pylint: disable=consider-using-with,duplicate-code
            proc = subprocess.Popen(
                hass_command,
                env=subprocess_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            try:
                assert proc.stdout is not None
                read_timeout = 60
                result, log = self._wait_for_line(
                    b"Starting Home Assistant",
                    out=proc.stdout,
                    read_timeout=read_timeout,
                )

                result_descriptions: Dict[DryRunHassTask.LineWaitResult, str] = {
                    "timeout": (
                        f"Timeout. Didn't receive any logs for {read_timeout}s"
                    ),
                    "crash": "HA process exited unexpectedly",
                    "ok": "HA successfully started up",
                }
                self.log(result_descriptions[result])
                if result == "crash":
                    self.log(
                        Padding(
                            log.decode("utf-8", "ignore"),
                            pad=(0, 0, 0, 3),
                        )
                    )
            finally:
                # Ask HA to terminate if it is still running
                if proc.poll() is None:
                    self.log("Asking HA to stop")
                    proc.send_signal(SIGINT)
                    try:
                        proc.wait(15)
                        self.log("HA stopped")
                    except TimeoutError:
                        self.log("HA didn't react to SIGINT, killing")
                        proc.kill()

            if result != "ok":
                raise TaskException("Task failed")

    @staticmethod
    def _wait_for_line(
        line_to_wait_for: bytes,
        out: IO[bytes],
        read_timeout: int,
    ) -> Tuple[LineWaitResult, bytes]:
        make_nonblocking(out)
        startup_result: Optional[DryRunHassTask.LineWaitResult] = None

        # Scan logs
        line_tracker = LineTracker()
        log = BytesIO()
        with DefaultSelector() as selector:
            selector.register(out, EVENT_READ)
            while startup_result is None:
                if len(selector.select(read_timeout)) == 0:
                    # Timeout
                    startup_result = "timeout"
                else:
                    data = out.read()
                    if len(data) == 0:
                        # EOF
                        startup_result = "crash"
                    else:
                        log.write(data)
                        lines = line_tracker.lines(data)
                        if any(line_to_wait_for in line for line in lines):
                            startup_result = "ok"
        return (startup_result, log.getvalue())
