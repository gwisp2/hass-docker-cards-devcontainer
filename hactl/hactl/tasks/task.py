from abc import ABC, abstractmethod
from typing import Optional

from .task_context import TaskContext


class Task(ABC):
    name: str
    _context: Optional[TaskContext]

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.context = None

    def execute(self, context: TaskContext):
        self._context = context
        try:
            self.run()
            self._complete("changed")
        except KeyboardInterrupt:
            self._complete("cancelled")
            raise
        except Exception:
            self._complete("failed")
            raise

    @abstractmethod
    def run(self):
        ...

    def _complete(self, status: TaskContext.Status):
        assert self._context is not None
        if self._context.status() == "running":
            self._context.set_status(status)
