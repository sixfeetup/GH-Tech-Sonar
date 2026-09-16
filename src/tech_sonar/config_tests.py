from pathlib import Path

import pytest

from tech_sonar import config
from tech_sonar import model


def test_repository_parse() -> None:
    repository = model.Repository.parse("sixfeetup/GH-Tech-Sonar")

    assert repository.owner == "sixfeetup"
    assert repository.name == "GH-Tech-Sonar"
    assert str(repository) == "sixfeetup/GH-Tech-Sonar"


@pytest.mark.parametrize(
    "value",
    [
        "GH-Tech-Sonar",
        "sixfeetup/",
        "/GH-Tech-Sonar",
        "sixfeetup/GH-Tech-Sonar/extra",
    ],
)
def test_repository_rejects_invalid_names(value: str) -> None:
    with pytest.raises(ValueError, match="OWNER/REPOSITORY"):
        model.Repository.parse(value)


def test_load_config(tmp_path: Path) -> None:
    path = tmp_path / "sonar.toml"
    path.write_text('repository = "sixfeetup/GH-Tech-Sonar"\n')

    loaded = config.load_config(path)

    assert loaded == config.Config(
        repository=model.Repository("sixfeetup", "GH-Tech-Sonar"),
    )


def test_load_config_reports_missing_repository(tmp_path: Path) -> None:
    path = tmp_path / "sonar.toml"
    path.write_text("")

    with pytest.raises(config.ConfigError, match="repository"):
        config.load_config(path)
