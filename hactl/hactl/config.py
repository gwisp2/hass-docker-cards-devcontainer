import re
from abc import ABC, abstractmethod
from functools import reduce
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Extra, Field, root_validator, validator
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
    path: Optional[Path]
    git: Optional[str]

    @validator("path")
    @classmethod
    def validate_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError(f"'path' value must be an absolute path: {value}")
        if not value.exists():
            raise ValueError(f"{value} does not exist")
        return value

    @root_validator(skip_on_failure=True)
    @classmethod
    def check_source_is_set(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        path = values.get("path")
        git = values.get("git")
        if path is None and git is None:
            raise ValueError("Either path or git must be set")
        if path is not None and git is not None:
            raise ValueError("path and git must not be used at the same time")
        return values


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
