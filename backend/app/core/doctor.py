import httpx

from app.core.neo4j_client import verify_connectivity
from app.core.settings import get_settings


def run_checks() -> dict[str, bool]:
    settings = get_settings()
    checks: dict[str, bool] = {}

    try:
        checks["neo4j"] = verify_connectivity(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
    except Exception:
        checks["neo4j"] = False

    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        checks["ollama"] = settings.ollama_model in models
    except Exception:
        checks["ollama"] = False

    return checks


if __name__ == "__main__":
    results = run_checks()
    for name, ok in results.items():
        print(f"{'OK  ' if ok else 'FAIL'}  {name}")