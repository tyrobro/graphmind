import httpx
import pytest

from app.core.settings import get_settings


@pytest.mark.sprint0
@pytest.mark.live
def test_ollama_model_available():
    s = get_settings()
    resp = httpx.get(f"{s.ollama_base_url}/api/tags", timeout=10)
    resp.raise_for_status()
    names = [m["name"] for m in resp.json().get("models", [])]
    assert s.ollama_model in names, f"{s.ollama_model} not found in {names}"