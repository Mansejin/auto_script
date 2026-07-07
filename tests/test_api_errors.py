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


def test_quota_error():
    msg = friendly_api_error("429 RESOURCE_EXHAUSTED quota exceeded")
    assert "한도" in msg


def test_short_value_error_passthrough():
    msg = friendly_api_error(ValueError("세특 과목이 지정되지 않았습니다."))
    assert msg == "세특 과목이 지정되지 않았습니다."
