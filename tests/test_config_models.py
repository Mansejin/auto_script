from src.saenggibu.config import gemini_models_for_api, get_gemini_model_fast, get_gemini_model_pro


def test_gemini_model_pro_default(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL_PRO", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    assert get_gemini_model_pro() == "gemini-3.1-pro-preview"


def test_gemini_model_pro_explicit(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PRO", "custom-pro")
    monkeypatch.setenv("GEMINI_MODEL", "legacy")
    assert get_gemini_model_pro() == "custom-pro"


def test_gemini_model_fast_default(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL_FAST", raising=False)
    assert get_gemini_model_fast() == "gemini-2.5-flash"


def test_gemini_models_for_api(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PRO", "pro-model")
    monkeypatch.setenv("GEMINI_MODEL_FAST", "flash-model")
    models = gemini_models_for_api()
    assert models["gemini_model"] == "flash-model"
    assert models["gemini_model_pro"] == "pro-model"
    assert models["gemini_model_fast"] == "flash-model"
    assert models["gemini_model_default"] == "fast"
