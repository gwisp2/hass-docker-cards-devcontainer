import os
from pathlib import Path
from typing import List, Optional

from rich.markup import escape

from hactl.config import HactlConfig
from hactl.tasks.commons import TaskException

from .git_utils import GitUtils
from .task import Task


class SetupCustomComponentsTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Downloading and linking custom components")
        self.cfg = cfg
        self.git_utils = GitUtils(self)

    def run(self) -> None:
        if len(self.cfg.customComponents) == 0:
            # Don't return
            # We still need to remove old symlinks
            self.log("No custom components configured")

        custom_components_path = self.cfg.paths.data / "custom_components"
        custom_components_path.mkdir(exist_ok=True)

        valid_symlinks: List[Path] = []
        for component_cfg in self.cfg.customComponents:
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

            # Find component roots
            component_roots = [m.parent for m in manifests]

            # Symlink components
            for component_root in component_roots:
                link_path = self._link_custom_component(
                    custom_components_path, component_root
                )
                valid_symlinks.append(link_path)

        # Remove old symlinks
        for name in os.listdir(custom_components_path):
            component_dir = custom_components_path / name
            if component_dir.is_symlink() and component_dir not in valid_symlinks:
                component_dir.unlink()
                self.log(f"{escape(str(component_dir))} removed")

    def _link_custom_component(
        self, custom_components_path: Path, component_root: Path
    ) -> Path:
        component_link_path = custom_components_path / component_root.name
        action_prefix: Optional[str] = None
        if component_link_path.exists():
            current_link_target = Path(os.readlink(component_link_path))
            if current_link_target != component_root:
                component_link_path.unlink()
                action_prefix = "(modified) "
            else:
                action_prefix = None
        else:
            action_prefix = "(new) "

        # Check for existance again
        # If a link exists then it is correct now
        if not component_link_path.exists():
            self.log(
                f"[yellow]{action_prefix}[/yellow][blue]"
                f"{escape(str(component_link_path))}[/]"
                f" -> [blue]{escape(str(component_root))}[/]"
            )
            os.symlink(component_root, component_link_path, target_is_directory=True)
        else:
            self.log(f"{escape(str(component_link_path))} is ok")

        return component_link_path
