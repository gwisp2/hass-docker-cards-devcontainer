#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from typing import List, Literal

import debugpy
from rich.console import Console

from hactl.config import DirConfigSource, FilesConfigSource
from hactl.ha_runner import HaRunner
from hactl.tasks import (
    BypassOnboardingTask,
    CreateHassUserTask,
    DryRunHassTask,
    EnsureHassConfigExistsTask,
    InstallHacsTask,
    InstallHaTask,
    SetupCustomComponentsTask,
    SetupLovelaceTask,
    TaskContextImpl,
)

from .tasks.task import Task

CMD_SETUP = "setup"
CMD_CONFIGURE = "configure"
CMD_RUN = "run"
CMD_TYPES = [CMD_SETUP, CMD_CONFIGURE, CMD_RUN]
CmdType = Literal["setup", "configure", "run"]


def perform_tasks(console: Console, tasks: List[Task]) -> None:
    for task in tasks:
        ctx = TaskContextImpl(console)
        task.execute(ctx)

        if ctx.status() != "ok":
            # Early exit on failure
            sys.exit(1)


def start_debug_adapter() -> None:
    debugpy.listen(5678)


def main() -> None:
    start_debug_adapter()

    console = Console(highlight=False)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Control Home Assistant")
    parser.add_argument(
        "-c",
        dest="configs",
        metavar="CONFIG",
        action="append",
        required=False,
        type=Path,
        help="configuration file",
    )
    parser.add_argument("command", type=str, choices=CMD_TYPES)
    parser.add_argument(
        "--wait-for-debugger",
        dest="wait_for_debugger",
        action="store_const",
        const=True,
    )

    args = parser.parse_args()
    config_paths: List[Path] = args.configs
    command: CmdType = args.command

    if args.wait_for_debugger:
        console.print("Waiting for debugger...")
        debugpy.wait_for_client()

    # Use default config_paths if not defined
    if config_paths is None:
        default_config_root = Path("/etc/hactl")
        config_paths = list(default_config_root.glob("*"))
        if len(config_paths) == 0:
            console.print(f"No configuration found in [blue]{default_config_root}[/]")
            console.print("Add some files there or use -c to provide config paths")
            sys.exit(2)
        config_source = DirConfigSource(default_config_root)
    else:
        config_source = FilesConfigSource(config_paths)

    # Convert config to Config class
    if command == CMD_SETUP:
        cfg = config_source.load_config()
        tasks = [
            InstallHaTask(cfg),
            EnsureHassConfigExistsTask(cfg),
            CreateHassUserTask(cfg),
            BypassOnboardingTask(cfg),
            SetupLovelaceTask(cfg),
            SetupCustomComponentsTask(cfg),
            InstallHacsTask(cfg),
            DryRunHassTask(cfg),
        ]
        perform_tasks(console, tasks)
    elif command == CMD_CONFIGURE:
        cfg = config_source.load_config()
        tasks = [SetupLovelaceTask(cfg), SetupCustomComponentsTask(cfg)]
        perform_tasks(console, tasks)
    elif command == CMD_RUN:
        runner = HaRunner(config_source, console)
        runner.run()


if __name__ == "__main__":
    main()
