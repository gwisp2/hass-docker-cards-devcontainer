from abc import ABC, abstractmethod
from typing import Literal
from rich.console import RenderableType


class TaskContext(ABC):
    Status = Literal["running", "failed", "cancelled", "changed", "no changes"]

    @abstractmethod
    def log(self, renderable: RenderableType):
        ...

    @abstractmethod
    def set_status(self, status: Status):
        ...

    @abstractmethod
    def status(self) -> Status:
        ...
