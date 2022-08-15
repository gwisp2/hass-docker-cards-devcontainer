#!/usr/bin/env python3


import sys

from rich.console import Console

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


def main() -> None:
    console = Console(highlight=False)
    cfg = HactlConfig.parse_raw(
        """
        lovelace:
            plugins: [
                    "thomasloven/lovelace-card-mod",
                    "thomasloven/lovelace-auto-entities",
                    "custom-cards/button-card",
            ]
            extra_files: ["dist/l.js"]
    """,
        proto="yaml",
    )
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
