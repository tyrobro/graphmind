import pytest

from app.core.neo4j_client import verify_connectivity
from app.core.settings import get_settings


@pytest.mark.sprint0
def test_neo4j_returns_1():
    s = get_settings()
    assert verify_connectivity(s.neo4j_uri, s.neo4j_user, s.neo4j_password) is True