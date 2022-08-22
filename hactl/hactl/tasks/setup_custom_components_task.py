from pathlib import Path
from typing import List

from rich.markup import escape

from hactl.config import HactlConfig
from hactl.tasks.util.git_utils import GitUtils
from hactl.tasks.util.symlink_helper import make_name_to_path_dict, update_symlinks
from hactl.tasks.util.types import TaskException

from .task import Task


class SetupCustomComponentsTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Downloading and linking custom components")
        self.cfg = cfg
        self.git_utils = GitUtils(self)

    def run(self) -> None:
        if len(self.cfg.components) == 0:
            # Don't return
            # We still need to remove old symlinks
            self.log("No custom components configured")

        custom_components_path = self.cfg.ha.data / "custom_components"
        custom_components_path.mkdir(exist_ok=True)

        component_roots: List[Path] = []
        for component_cfg in self.cfg.components:
            if component_cfg.git:
                # Download from git
                worktree = self.git_utils.get_from_git(component_cfg.git)
                # Process downloaded component as a local one
                component_cfg.path = worktree

            # These must be checked in config validator
            assert component_cfg.path is not None
            assert component_cfg.path.is_absolute()
            assert component_cfg.path.exists()

            # Find component manifest files
            manifests = list(component_cfg.path.glob("**/manifest.json"))
            if len(manifests) == 0:
                raise TaskException(
                    f"{escape(str(component_cfg.path))} -> no manifest found"
                )

            component_roots.extend(m.parent for m in manifests)

        update_symlinks(
            custom_components_path, make_name_to_path_dict(component_roots), self
        )
