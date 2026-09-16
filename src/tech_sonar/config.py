import dataclasses
import pathlib
import tomllib

from tech_sonar import model


class ConfigError(ValueError):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class Config:
    repository: model.Repository


def load_config(path: pathlib.Path) -> Config:
    try:
        values = tomllib.loads(path.read_text())
        repository_value = values["repository"]
    except FileNotFoundError as error:
        raise ConfigError(f"configuration file not found: {path}") from error
    except (tomllib.TOMLDecodeError, KeyError) as error:
        raise ConfigError(
            f"{path} must define repository in OWNER/REPOSITORY form",
        ) from error

    if not isinstance(repository_value, str):
        raise ConfigError(
            f"{path} repository must be a string in OWNER/REPOSITORY form",
        )

    try:
        repository = model.Repository.parse(repository_value)
    except ValueError as error:
        raise ConfigError(f"{path}: {error}") from error

    return Config(repository=repository)
