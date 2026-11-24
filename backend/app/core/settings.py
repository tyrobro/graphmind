from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "graphmind_dev_password"

    sqlite_path: str = "./data/graphmind.db"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b-instruct-q4_K_M"

    memory_pressure_threshold: float = 0.80
    alpha: float = 0.5
    beta: float = 0.5
    min_node_age_seconds: int = 300
    prune_undo_window_hours: int = 24
    edge_decay_factor: float = 0.7

    @field_validator("memory_pressure_threshold")
    @classmethod
    def _threshold_in_range(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError(
                f"memory_pressure_threshold must be in (0, 1], got {v}"
            )
        return v

    @field_validator("alpha", "beta", "edge_decay_factor")
    @classmethod
    def _non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"value must be >= 0, got {v}")
        return v

    @field_validator("min_node_age_seconds", "prune_undo_window_hours")
    @classmethod
    def _positive_int(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"value must be >= 0, got {v}")
        return v


def get_settings() -> Settings:
    return Settings()