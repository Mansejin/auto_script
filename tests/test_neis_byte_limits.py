from __future__ import annotations

from src.saenggibu.inspector.rules import DEFAULT_BYTE_LIMITS
from src.saenggibu.neis_counter import neis_counter_byte_len


def test_neis_counter_byte_len_korean() -> None:
    assert neis_counter_byte_len("가") == 3
    assert neis_counter_byte_len("abc") == 3


def test_byte_limits_match_neis_counter_2026() -> None:
    assert DEFAULT_BYTE_LIMITS["행발"]["hard_max"] == 900
    assert DEFAULT_BYTE_LIMITS["세특"]["hard_max"] == 1500
    assert DEFAULT_BYTE_LIMITS["창체"]["hard_max"] == 1500
