import os

from rich.markup import escape

from hactl.config import HactlConfig
from hactl.tasks.commons import TaskException

from .task import Task


class SetupCustomComponentsTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Linking custom components")
        self.cfg = cfg

    def run(self) -> None:
        if len(self.cfg.customComponents) == 0:
            self.log("No custom components configured")
            return

        custom_components_path = self.cfg.paths.data / "custom_components"
        custom_components_path.mkdir(exist_ok=True)

        for component_cfg in self.cfg.customComponents:
            component_path = component_cfg.path.absolute()
            if not component_path.exists():
                raise TaskException(f"'{component_path}' does not exist")

            component_link_path = (
                custom_components_path / component_cfg.effective_name()
            )

            if component_link_path.exists():
                link_target = os.readlink(component_link_path)
                if link_target != component_path:
                    self.log(
                        f"[blue]{escape(str(component_link_path))}[/]"
                        f"links to [blue]{escape(str(link_target))}[/], removing"
                    )
                    os.unlink(component_link_path)
                else:
                    self.log(
                        f"[blue]{escape(str(component_link_path))}[/] already exists"
                    )
                    continue

            self.log(
                f"Linking [blue]{escape(str(component_link_path))}[/]"
                f" to [blue]{escape(str(component_path))}[/]"
            )
            os.symlink(component_path, component_link_path, target_is_directory=True)
