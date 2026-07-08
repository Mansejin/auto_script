from src.saenggibu.model_routing import plan_sample_analysis, plan_write_section, summarize_plan


def test_plan_sample_analysis_uses_pro(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PRO", "pro-fixed")
    steps = plan_sample_analysis()
    assert len(steps) == 1
    assert steps[0].model == "pro-fixed"
    assert steps[0].tier == "pro"


def test_plan_haengbal_uses_flash(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_FAST", "flash-default")
    steps = plan_write_section("행발")
    assert len(steps) == 1
    assert steps[0].model == "flash-default"
    assert steps[0].tier == "fast"


def test_plan_setuk_multiple_subjects(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_FAST", "flash-only")
    steps = plan_write_section("세특", subject_count=2)
    assert len(steps) == 2
    assert all(s.model == "flash-only" for s in steps)
    counts = summarize_plan(steps)
    assert counts == {"flash-only": 2}
