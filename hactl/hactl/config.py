from abc import ABC, abstractmethod
from functools import reduce
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Extra
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


class LovelaceConfig(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    plugins: List[str]
    extra_files: List[Path]


class HactlConfig(
    YamlModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    paths: HactlPaths
    user: UserCredentials
    lovelace: LovelaceConfig
    version: Optional[str]


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
