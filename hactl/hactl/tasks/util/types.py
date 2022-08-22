from typing import Protocol, TypeAlias, Union

from rich.console import RenderableType


class HasFileno(Protocol):  # pylint: disable=too-few-public-methods
    def fileno(self) -> int:
        ...


FileDescriptor: TypeAlias = int
FileDescriptorLike: TypeAlias = Union[int, HasFileno]


class TaskException(Exception):
    message: RenderableType

    def __init__(self, renderable: RenderableType) -> None:
        super().__init__()
        self.message = renderable
