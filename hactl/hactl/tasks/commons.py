import os
import shlex
import subprocess
from pathlib import Path, PurePath
from typing import List, Union

from rich.console import Group, RenderableType
from rich.markup import escape
from rich.padding import Padding


class TaskException(Exception):
    message: RenderableType

    def __init__(self, renderable: RenderableType) -> None:
        super().__init__()
        self.message = renderable


def run_command(
    command_ex: List[Union[str, PurePath]],
    reset_pythonpath: bool = True,
    catch_output: bool = True,
    raise_on_error: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    # Convert paths to strings
    command: List[str] = [str(arg) for arg in command_ex]

    if reset_pythonpath:
        # Forbid using non-virtualenv packages by clearing PYTHONPATH
        subprocess_env = dict(os.environ)
        subprocess_env.pop("PYTHONPATH", None)
    else:
        subprocess_env = None

    if catch_output:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=subprocess_env,
        )
    else:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL, check=False, env=subprocess_env
        )

    # Return result if ok or if errors are ignored
    if result.returncode == 0 or not raise_on_error:
        return result

    # Raise exception with the error message
    # pylint: disable=line-too-long
    raise TaskException(
        Group(
            f"Command [red]{escape(shlex.join(command))}[/] exited with exit code [red]{result.returncode}[/]",  # noqa: E501
            Padding(
                escape(result.stdout.decode("utf-8", errors="ignore")),
                pad=(0, 0, 0, 2),
            ),
        )
    )


def run_hass_command(venv: Path, data_path: Path, args: List[Union[str, Path]]) -> None:
    run_command([venv / "bin" / "hass", "-c", data_path, *args])
