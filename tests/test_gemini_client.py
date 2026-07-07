from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.saenggibu import gemini_client as gc


def test_classify_rate_limit():
    assert gc._classify_error(RuntimeError("429 RESOURCE_EXHAUSTED")) is gc._ErrorKind.RATE_LIMIT
    assert gc._classify_error(RuntimeError("requests per minute")) is gc._ErrorKind.RATE_LIMIT


def test_classify_transient():
    assert gc._classify_error(RuntimeError("503 UNAVAILABLE high demand")) is gc._ErrorKind.TRANSIENT


def test_classify_fatal():
    assert gc._classify_error(ValueError("bad input")) is gc._ErrorKind.FATAL


@patch("src.saenggibu.gemini_client._client")
@patch("src.saenggibu.gemini_client._throttle")
def test_generate_text_uses_fast_tier(mock_throttle: MagicMock, mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_MODEL_FAST", "flash-test")
    api = mock_client.return_value
    response = MagicMock()
    response.text = "ok"
    api.models.generate_content.return_value = response

    text = gc.generate_text(system="s", user="u", tier="fast")
    assert text == "ok"
    assert api.models.generate_content.call_args.kwargs["model"] == "flash-test"


@patch("src.saenggibu.gemini_client._client")
@patch("src.saenggibu.gemini_client._throttle")
def test_no_retry_on_rate_limit(mock_throttle: MagicMock, mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_MAX_RETRIES", "2")
    api = mock_client.return_value
    api.models.generate_content.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED rate limit")

    with pytest.raises(RuntimeError, match="분당|일시"):
        gc.generate_text(system="s", user="u")

    assert api.models.generate_content.call_count == 1


@patch("src.saenggibu.gemini_client._client")
@patch("src.saenggibu.gemini_client._throttle")
@patch("src.saenggibu.gemini_client.time.sleep")
def test_retry_only_transient_when_configured(
    mock_sleep: MagicMock,
    mock_throttle: MagicMock,
    mock_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("GEMINI_MAX_RETRIES", "1")
    api = mock_client.return_value
    response = MagicMock()
    response.text = "ok"
    api.models.generate_content.side_effect = [
        RuntimeError("503 UNAVAILABLE high demand"),
        response,
    ]

    text = gc.generate_text(system="s", user="u")
    assert text == "ok"
    assert api.models.generate_content.call_count == 2
    mock_sleep.assert_called_once()


@patch("src.saenggibu.gemini_client._client")
@patch("src.saenggibu.gemini_client._throttle")
def test_default_no_retry_on_transient(mock_throttle: MagicMock, mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GEMINI_MAX_RETRIES", raising=False)
    api = mock_client.return_value
    api.models.generate_content.side_effect = RuntimeError("503 UNAVAILABLE")

    with pytest.raises(RuntimeError):
        gc.generate_text(system="s", user="u")

    assert api.models.generate_content.call_count == 1
