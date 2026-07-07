from src.saenggibu.api_errors import friendly_api_error


def test_gemini_503_high_demand():
    raw = (
        "503 UNAVAILABLE. {'error': {'code': 503, "
        "'message': 'This model is currently experiencing high demand. "
        "Spikes in demand are usually temporary. Please try again later.', "
        "'status': 'UNAVAILABLE'}}"
    )
    msg = friendly_api_error(raw)
    assert "과부하" in msg
    assert "{" not in msg


def test_resource_exhausted_not_monthly_quota():
    raw = (
        "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, "
        "'message': 'Resource has been exhausted (e.g. check quota).', "
        "'status': 'RESOURCE_EXHAUSTED'}}"
    )
    msg = friendly_api_error(raw)
    assert "월간" not in msg
    assert "일시" in msg or "분당" in msg


def test_rate_limit_per_minute():
    msg = friendly_api_error("429 rate limit exceeded: requests per minute")
    assert "분당" in msg
    assert "한도는 남아" in msg


def test_model_capacity():
    msg = friendly_api_error(
        "429 No capacity available for model gemini-3.1-pro-preview MODEL_CAPACITY_EXHAUSTED"
    )
    assert "가득" in msg or "일시" in msg


def test_app_free_limit_passthrough():
    raw = "이번 달 무료 작성 한도(10건)를 모두 사용했습니다."
    assert friendly_api_error(raw) == raw


def test_short_value_error_passthrough():
    msg = friendly_api_error(ValueError("세특 과목이 지정되지 않았습니다."))
    assert msg == "세특 과목이 지정되지 않았습니다."
