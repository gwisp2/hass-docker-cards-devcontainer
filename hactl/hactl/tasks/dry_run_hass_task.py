import fcntl
import os
import subprocess
import tempfile
from io import BytesIO
from selectors import EVENT_READ, DefaultSelector
from signal import SIGINT
from typing import IO, Dict, Literal, Optional, Tuple

from rich.padding import Padding

from hactl.config import HactlConfig
from hactl.tasks.commons import TaskException

from .task import Task


class DryRunHassTask(Task):
    LineWaitResult = Literal["timeout", "crash", "ok"]

    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Running Home Assistant to install missing packages")
        self.cfg = cfg

    def run(self) -> None:
        hass_path = self.cfg.paths.venv / "bin" / "hass"

        # Forbid using non-virtualenv packages
        subprocess_env = dict(os.environ)
        subprocess_env.pop("PYTHONPATH", None)

        # Run HA in a temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Start HA
            hass_command = [str(hass_path), "-c", str(tmp_dir), "-v"]

            # pylint: disable=consider-using-with
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
    def _make_nonblocking(out: IO[bytes]) -> None:
        pipe_fd = out.fileno()
        pipe_fl = fcntl.fcntl(pipe_fd, fcntl.F_GETFL)
        fcntl.fcntl(pipe_fd, fcntl.F_SETFL, pipe_fl | os.O_NONBLOCK)

    @staticmethod
    def _wait_for_line(
        line_to_wait_for: bytes,
        out: IO[bytes],
        read_timeout: int,
    ) -> Tuple[LineWaitResult, bytes]:
        DryRunHassTask._make_nonblocking(out)
        startup_result: Optional[DryRunHassTask.LineWaitResult] = None

        # Scan logs
        unprocessed_bytes = b""
        log = BytesIO()
        selector = DefaultSelector()
        selector.register(out, EVENT_READ)
        try:
            while startup_result is None:
                events_list = selector.select(read_timeout)
                if len(events_list) == 0:
                    # Timeout
                    startup_result = "timeout"
                else:
                    bytes_read = out.read()
                    log.write(bytes_read)

                    if len(bytes_read) == 0:
                        # EOF
                        startup_result = "crash"
                    else:
                        # Process bytes
                        last_bytes = unprocessed_bytes + bytes_read
                        lines = last_bytes.split(b"\n")

                        # Search for line_to_wait_for
                        line_found = (
                            next(
                                (line for line in lines if line_to_wait_for in line),
                                None,
                            )
                            is not None
                        )

                        if line_found:
                            # Startup completed
                            startup_result = "ok"

                        # Remember uncompleted line
                        unprocessed_bytes = lines[-1]
        finally:
            selector.close()

        return (startup_result, log.getvalue())