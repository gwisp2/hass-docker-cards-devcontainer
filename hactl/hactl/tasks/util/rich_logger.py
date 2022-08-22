from abc import abstractmethod
from typing import Protocol

from rich.console import RenderableType


class RichLogger(Protocol):  # pylint:disable=too-few-public-methods
    @abstractmethod
    def log(self, renderable: RenderableType) -> None:
        raise NotImplementedError
