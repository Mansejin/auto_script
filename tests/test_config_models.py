from src.saenggibu.config import gemini_models_for_api, get_gemini_model_pro


def test_gemini_model_pro_default(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL_PRO", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    assert get_gemini_model_pro() == "gemini-3.1-pro-preview"


def test_gemini_models_for_api(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PRO", "pro-model")
    models = gemini_models_for_api()
    assert models["gemini_model"] == "pro-model"
    assert models["gemini_model_pro"] == "pro-model"
    assert "gemini_model_fast" not in models
