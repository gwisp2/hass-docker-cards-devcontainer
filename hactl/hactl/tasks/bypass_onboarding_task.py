from hactl.config import HactlConfig

from .task import Task


class BypassOnboardingTask(Task):
    def __init__(self, cfg: HactlConfig) -> None:
        super().__init__("Bypassing onboarding")
        self.cfg = cfg

    def run(self) -> None:
        dot_storage_path = self.cfg.ha.data / ".storage"
        dot_storage_path.mkdir(exist_ok=True)
        onboarding_data_file = dot_storage_path / "onboarding"
        onboarding_data_file.write_text(
            """
        {
            "data": {
                "done": [
                    "user",
                    "core_config",
                    "integration"
                ]
            },
            "key": "onboarding",
            "version": 3
        }
        """,
            encoding="utf-8",
        )
