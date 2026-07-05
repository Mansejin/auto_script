from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENC_MARKER = "__enc"
ENC_VERSION = "v1"


def encrypt_data_enabled() -> bool:
    if os.getenv("SGB_ENCRYPT_DATA", "1").strip().lower() in ("0", "false", "no"):
        return False
    return bool(get_data_key())


def get_data_key() -> bytes | None:
    raw = os.getenv("SGB_DATA_KEY", "").strip()
    if not raw:
        return None
    try:
        key = base64.urlsafe_b64decode(raw + "=="[: (4 - len(raw) % 4) % 4])
    except Exception:
        key = hashlib.sha256(raw.encode("utf-8")).digest()
    if len(key) not in (16, 24, 32):
        key = hashlib.sha256(key).digest()
    return key


def encrypt_json(data: Any) -> dict[str, str]:
    key = get_data_key()
    if not key:
        raise RuntimeError("SGB_DATA_KEY가 설정되지 않았습니다.")
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return {ENC_MARKER: ENC_VERSION, "payload": payload}


def decrypt_json(wrapper: dict[str, Any]) -> Any:
    key = get_data_key()
    if not key:
        raise RuntimeError("SGB_DATA_KEY가 설정되지 않았습니다.")
    if wrapper.get(ENC_MARKER) != ENC_VERSION:
        raise ValueError("지원하지 않는 암호화 형식입니다.")
    raw = base64.urlsafe_b64decode(str(wrapper["payload"]).encode("ascii"))
    nonce, ciphertext = raw[:12], raw[12:]
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))
