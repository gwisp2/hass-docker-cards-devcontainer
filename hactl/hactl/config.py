import re
from abc import ABC, abstractmethod
from functools import reduce
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Extra, Field
from pydantic_yaml import YamlModel
from ruamel.yaml import YAML


class HactlPaths(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    venv: Path
    data: Path


class UserCredentials(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    name: str
    password: str


class CustomComponentLink(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    path: Path
    name: Optional[str]

    def effective_name(self) -> str:
        return self.name if self.name is not None else self.path.name


class LovelaceConfig(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    plugins: List[str]
    extra_files: List[Path]


class LoggingColorRule(BaseModel, extra=Extra.forbid, arbitrary_types_allowed=True):
    pattern: re.Pattern[str] = re.compile("")  # Silence pydantic
    line_color: str = Field(regex="^[a-z]+$")

    def __init__(self, **data: Any) -> None:
        pattern: str = data["pattern"]
        del data["pattern"]
        super().__init__(**data)
        self.pattern = re.compile(pattern)


class LoggingConfig(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    colors: List[LoggingColorRule] = []

    def color_for_line(self, line: str) -> Optional[str]:
        return next(
            (c.line_color for c in self.colors if c.pattern.fullmatch(line)), None
        )


class HactlConfig(
    YamlModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    paths: HactlPaths
    user: UserCredentials
    customComponents: List[CustomComponentLink] = []
    lovelace: LovelaceConfig
    version: Optional[str]
    logging: LoggingConfig


class ConfigSource(ABC):  # pylint: disable=too-few-public-methods
    @abstractmethod
    def load_config(self) -> HactlConfig:
        ...

    def _from_files(self, config_paths: List[Path]) -> HactlConfig:
        # Read config files
        yaml = YAML()
        configs = []
        for config_path in config_paths:
            configs.append(yaml.load(config_path.read_text("utf-8")))

        # Merge configs & print merged config
        merged_config = reduce(self._merge_configs, configs)

        # Convert config to Config class
        return HactlConfig(**merged_config)

    def _merge_configs(self, lhs: Any, rhs: Any) -> Any:
        if isinstance(lhs, dict):
            if not isinstance(rhs, dict):
                raise ValueError("Can't merge {rhs} into {lhs}")

            result = dict(lhs)
            for key, value in rhs.items():
                c1v = lhs.get(key)
                if c1v is not None:
                    value = self._merge_configs(c1v, value)
                result[key] = value
            return result

        if isinstance(lhs, list):
            if not isinstance(rhs, list):
                raise ValueError("Can't merge {rhs} into {lhs}")
            return [*lhs, *rhs]

        return rhs


class FilesConfigSource(ConfigSource):  # pylint: disable=too-few-public-methods
    def __init__(self, files: List[Path]) -> None:
        super().__init__()
        self.files = files

    def load_config(self) -> HactlConfig:
        return self._from_files(self.files)


class DirConfigSource(ConfigSource):  # pylint: disable=too-few-public-methods
    def __init__(self, configs_dir: Path) -> None:
        super().__init__()
        self.configs_dir = configs_dir

    def load_config(self) -> HactlConfig:
        paths = [*self.configs_dir.glob("*")]
        paths.sort(key=lambda p: p.name)
        return self._from_files(paths)
