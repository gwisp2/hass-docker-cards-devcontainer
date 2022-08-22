from abc import ABC, abstractmethod
from typing import Optional, final

from rich.console import RenderableType
from rich.traceback import Traceback

from .task_context import TaskContext
from .util.types import TaskException


class Task(ABC):
    name: str
    _context: Optional[TaskContext]

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.context = None

    @final
    def execute(self, context: TaskContext) -> None:
        self._context = context
        self._context.set_title(self.name)
        try:
            self.run()
            self._complete("ok")
        except KeyboardInterrupt:
            self._complete("cancelled")
        except TaskException as exc:
            self.log(exc.message)
            self._complete("failed")
        except Exception:  # pylint: disable=broad-except
            self.log("Unknown exception")
            self.log(Traceback())
            self._complete("failed")

    @abstractmethod
    def run(self) -> None:
        ...

    def log(self, renderable: RenderableType) -> None:
        assert self._context is not None
        self._context.log(renderable)

    def _complete(self, status: TaskContext.Status) -> None:
        assert self._context is not None
        self._context.complete_with_status(status)
