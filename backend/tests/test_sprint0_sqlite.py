import pytest

from app.core.db import write_read_roundtrip


@pytest.mark.sprint0
def test_sqlite_write_read(tmp_path):
    db_path = str(tmp_path / "test.db")
    assert write_read_roundtrip(db_path) == "sprint0-check"