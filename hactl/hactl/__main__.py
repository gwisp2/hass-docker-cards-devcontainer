#!/usr/bin/env python3


import argparse
import sys
from functools import reduce
from pathlib import Path
from typing import Any, List

from rich.console import Console
from ruamel.yaml import YAML

from hactl.config import HactlConfig
from hactl.tasks import (
    BypassOnboardingTask,
    CreateHassUserTask,
    DryRunHassTask,
    EnsureHassConfigExistsTask,
    InstallHacsTask,
    InstallHaTask,
    SetupLovelaceTask,
    TaskContextImpl,
)


def merge_configs(lhs: Any, rhs: Any) -> Any:
    if isinstance(lhs, dict):
        if not isinstance(rhs, dict):
            raise ValueError("Can't merge {rhs} into {lhs}")

        result = dict(lhs)
        for key, value in rhs.items():
            c1v = lhs.get(key)
            if c1v is not None:
                value = merge_configs(c1v, value)
            result[key] = value
        return result

    if isinstance(lhs, list):
        if not isinstance(rhs, list):
            raise ValueError("Can't merge {rhs} into {lhs}")
        return [*lhs, *rhs]

    return rhs


def main() -> None:
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
    parser.add_argument("-v", action="store_true")
    args = parser.parse_args()
    config_paths: List[Path] = args.configs
    verbose: bool = args.v

    # Use default config_paths if not defined
    if config_paths is None:
        default_config_root = "/etc/hactl"
        config_paths = list(Path("/etc/hactl").glob("*"))
        if len(config_paths) == 0:
            console.print(f"No configuration found in [blue]{default_config_root}[/]")
            console.print("Add some files there or use -c to provide config paths")
            sys.exit(2)
            return

    # Read config files
    yaml = YAML()
    configs = []
    for config_path in config_paths:
        configs.append(yaml.load(config_path.read_text("utf-8")))

    # Merge configs & print merged config
    merged_config = reduce(merge_configs, configs)
    if verbose:
        console.print("Config:")
        console.print_json(data=merged_config)

    # Convert config to Config class
    cfg = HactlConfig(**merged_config)

    tasks = [
        InstallHaTask(cfg),
        EnsureHassConfigExistsTask(cfg),
        CreateHassUserTask(cfg),
        BypassOnboardingTask(cfg),
        SetupLovelaceTask(cfg),
        InstallHacsTask(cfg),
        DryRunHassTask(cfg),
    ]

    for task in tasks:
        ctx = TaskContextImpl(console)
        task.execute(ctx)

        if ctx.status() != "ok":
            # Early exit on failure
            sys.exit(1)


if __name__ == "__main__":
    main()
