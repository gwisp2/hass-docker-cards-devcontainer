import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Extra, Field, root_validator, validator
from pydantic_yaml import YamlModel


class UserCredentials(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    name: str
    password: str


class HaConfig(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    version: Optional[str]
    venv: Path = Path("/henv")
    data: Path = Path("/hdata")
    user: UserCredentials = UserCredentials(name="dev", password="dev")


class LovelacePluginLink(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    path: Optional[Path]
    github: Optional[str]

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
        num_fields_set = len([v for v in values.values() if v is not None])
        if num_fields_set == 0:
            raise ValueError("One of 'path', 'github' must be set")
        if num_fields_set >= 2:
            raise ValueError("path, git and url must not be used at the same time")
        return values


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


class LoggerRule(BaseModel, extra=Extra.forbid, arbitrary_types_allowed=True):
    pattern: re.Pattern[str] = re.compile("")  # Silence pydantic
    line_color: str = Field(regex="^[a-z]+$")  # TODO: check color is valid

    def __init__(self, **data: Any) -> None:
        pattern: str = data["pattern"]
        del data["pattern"]
        super().__init__(**data)
        self.pattern = re.compile(pattern)


class LoggingConfig(
    BaseModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    defaults: bool = True
    rules: List[LoggerRule] = []

    @root_validator(skip_on_failure=True)
    @classmethod
    def add_default_rules(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        rules: List[LoggerRule] = list(values["rules"])
        if values["defaults"]:
            default_rules = [
                LoggerRule(pattern=".*ERROR.*", line_color="red"),
                LoggerRule(pattern=".*WARNING.*", line_color="yellow"),
            ]
            rules.extend(default_rules)
        return {**values, "rules": rules}

    def color_for_line(self, line: str) -> Optional[str]:
        return next(
            (c.line_color for c in self.rules if c.pattern.fullmatch(line)), None
        )


class HactlConfig(
    YamlModel, extra=Extra.forbid
):  # pylint: disable=too-few-public-methods
    ha: HaConfig = HaConfig()
    components: List[CustomComponentLink] = []
    lovelace: List[LovelacePluginLink] = []
    logging: LoggingConfig = LoggingConfig()


class ConfigSource:  # pylint: disable=too-few-public-methods
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def load_config(self) -> HactlConfig:
        if not self.config_path.exists():
            return HactlConfig()

        # Read config file
        config_content = self.config_path.read_bytes()

        # Parse config
        return HactlConfig.parse_raw(config_content, proto="YAML")  # type: ignore
