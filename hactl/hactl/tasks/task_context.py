from abc import ABC, abstractmethod
from typing import Literal

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.padding import Padding
from rich.status import Status


class TaskContext(ABC):
    Status = Literal["running", "failed", "cancelled", "ok"]

    @abstractmethod
    def set_title(self, title: str) -> None:
        ...

    @abstractmethod
    def log(self, renderable: RenderableType) -> None:
        ...

    @abstractmethod
    def complete_with_status(self, status: Status) -> None:
        ...

    @abstractmethod
    def status(self) -> Status:
        ...


class TaskContextImpl(TaskContext):
    def __init__(self, console: Console) -> None:
        super().__init__()
        self.console = console
        self.console.clear_live()  # Clear any previous Live

        self._title = ""
        self._status: TaskContext.Status = "running"
        self._output: Group = Group()
        self._live: Live = Live(
            self._output, console=self.console, auto_refresh=True, refresh_per_second=8
        )
        self._live.start()
        self._update_output_header()

    def set_title(self, title: str) -> None:
        self._title = title
        self._update_output_header()

    def log(self, renderable: RenderableType) -> None:
        self._output.renderables.append(
            Padding(renderable, pad=(0, 0, 0, 3), style="grey50")
        )
        self._live.refresh()

    def complete_with_status(self, status: TaskContext.Status) -> None:
        if self._status != "running":
            raise ValueError("Can't change status twice")
        if status == "running":
            raise ValueError("Can't set 'running' status")
        self._status = status
        self._update_output_header()
        self._live.stop()

    def status(self) -> TaskContext.Status:
        return self._status

    def _update_output_header(self) -> None:
        # Compute new header
        new_header: RenderableType
        if self._status == "running":
            new_header = Status(f" {self._title}", spinner="line")
        elif self._status == "ok":
            new_header = rf":white_check_mark: {self._title} \[[green]ok[/]]"
        elif self._status in ("failed", "cancelled"):
            new_header = rf":X: {self._title} \[[red]{self._status}[/]]"

        # Set new header
        if len(self._output.renderables) == 0:
            self._output.renderables.append(new_header)
        else:
            self._output.renderables[0] = new_header

        self._live.refresh()
