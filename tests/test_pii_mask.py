from __future__ import annotations

from src.saenggibu.pii_mask import mask_for_ai, mask_pii_enabled, mask_summary, mask_text


def test_mask_phone() -> None:
    text = "연락처는 010-1234-5678 입니다."
    masked = mask_text(text)
    assert "[전화번호]" in masked
    assert "010-1234-5678" not in masked


def test_mask_email() -> None:
    text = "이메일 hello.student@school.kr 로 문의"
    masked = mask_text(text)
    assert "[이메일]" in masked
    assert "hello.student@school.kr" not in masked


def test_mask_disabled() -> None:
    import os

    old = os.environ.get("SGB_MASK_PII")
    os.environ["SGB_MASK_PII"] = "0"
    try:
        assert mask_for_ai("010-1234-5678") == "010-1234-5678"
    finally:
        if old is None:
            os.environ.pop("SGB_MASK_PII", None)
        else:
            os.environ["SGB_MASK_PII"] = old


def test_mask_summary_counts() -> None:
    text = "01012345678 test@example.com"
    summary = mask_summary(text)
    assert summary.get("phone", 0) >= 1
    assert summary.get("email", 0) >= 1
