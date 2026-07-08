from src.saenggibu.config import get_gemini_model_profile, skip_gemini_proofread
from src.saenggibu.model_routing import plan_write_section, resolve_model_for_tier, summarize_plan


def test_profile_default_split(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL_PROFILE", raising=False)
    assert get_gemini_model_profile() == "split"


def test_profile_flash_aliases(monkeypatch):
    for raw in ("flash", "all-flash", "fast"):
        monkeypatch.setenv("GEMINI_MODEL_PROFILE", raw)
        assert get_gemini_model_profile() == "flash"


def test_profile_pro(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PROFILE", "pro")
    assert get_gemini_model_profile() == "pro"


def test_skip_proofread(monkeypatch):
    monkeypatch.setenv("GEMINI_SKIP_PROOFREAD", "1")
    assert skip_gemini_proofread() is True
    monkeypatch.delenv("GEMINI_SKIP_PROOFREAD", raising=False)
    assert skip_gemini_proofread() is False


def test_resolve_model_split_tiers(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PRO", "pro-x")
    monkeypatch.setenv("GEMINI_MODEL_FAST", "flash-x")
    monkeypatch.setenv("GEMINI_MODEL_PROFILE", "split")
    assert resolve_model_for_tier("pro") == "pro-x"
    assert resolve_model_for_tier("fast") == "flash-x"


def test_resolve_model_flash_overrides_tier(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PRO", "pro-x")
    monkeypatch.setenv("GEMINI_MODEL_FAST", "flash-x")
    monkeypatch.setenv("GEMINI_MODEL_PROFILE", "flash")
    assert resolve_model_for_tier("pro") == "flash-x"
    assert resolve_model_for_tier("fast") == "flash-x"


def test_plan_haengbal_split(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PROFILE", "split")
    monkeypatch.delenv("GEMINI_SKIP_PROOFREAD", raising=False)
    steps = plan_write_section("행발")
    assert len(steps) == 2
    assert steps[0].tier == "pro"
    assert steps[1].tier == "fast"


def test_plan_haengbal_skip_proofread(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PROFILE", "split")
    steps = plan_write_section("행발", skip_proofread=True)
    assert len(steps) == 1
    assert steps[0].step == "행발 작성"


def test_plan_setuk_multiple_subjects(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PROFILE", "flash")
    monkeypatch.setenv("GEMINI_MODEL_FAST", "flash-only")
    steps = plan_write_section("세특", subject_count=2, skip_proofread=False)
    assert len(steps) == 4
    assert all(s.model == "flash-only" for s in steps)
    counts = summarize_plan(steps)
    assert counts == {"flash-only": 4}
