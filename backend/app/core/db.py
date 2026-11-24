import os
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select


class HealthCheck(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    note: str = "ok"


def get_engine(sqlite_path: str):
    Path(os.path.dirname(sqlite_path) or ".").mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{sqlite_path}")
    SQLModel.metadata.create_all(engine)
    return engine


def write_read_roundtrip(sqlite_path: str) -> str:
    engine = get_engine(sqlite_path)
    with Session(engine) as session:
        row = HealthCheck(note="sprint0-check")
        session.add(row)
        session.commit()
        session.refresh(row)
        row_id = row.id
    with Session(engine) as session:
        fetched = session.exec(select(HealthCheck).where(HealthCheck.id == row_id)).one()
        return fetched.note