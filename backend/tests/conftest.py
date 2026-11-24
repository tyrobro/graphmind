import pytest

from app.core.settings import Settings


@pytest.fixture
def default_settings() -> Settings:
    return Settings()