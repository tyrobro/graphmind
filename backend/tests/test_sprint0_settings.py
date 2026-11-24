import pytest
from pydantic import ValidationError

from app.core.settings import Settings


@pytest.mark.sprint0
def test_defaults_load(default_settings):
    assert default_settings.ollama_model


@pytest.mark.sprint0
def test_invalid_threshold_rejected():
    with pytest.raises(ValidationError, match="memory_pressure_threshold"):
        Settings(memory_pressure_threshold=1.5)


@pytest.mark.sprint0
def test_negative_alpha_rejected():
    with pytest.raises(ValidationError):
        Settings(alpha=-0.1)