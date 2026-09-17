import pytest

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
