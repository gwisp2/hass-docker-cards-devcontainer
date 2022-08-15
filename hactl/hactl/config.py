from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Extra
from pydantic_yaml import YamlModel


class HactlPaths(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    venv: Path = Path.home() / "hass-venv"
    data: Path = Path.home() / "hass-data"


class UserCredentials(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    name: str
    password: str


class LovelaceConfig(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    plugins: List[str] = []
    extra_files: List[Path] = []


class HactlConfig(
    YamlModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    paths: HactlPaths = HactlPaths()
    user: UserCredentials = UserCredentials(name="dev", password="dev")
    lovelace: LovelaceConfig = LovelaceConfig()
    version: Optional[str]
