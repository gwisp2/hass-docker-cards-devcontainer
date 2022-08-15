from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Extra
from pydantic_yaml import YamlModel


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
