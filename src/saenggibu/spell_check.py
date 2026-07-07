from __future__ import annotations

from .gemini_client import generate_text

_SYSTEM = (
    "당신은 한국어 맞춤법·띄어쓰기 교정 전문가입니다.\n"
    "고등학교 생활기록부 문장의 의미·사실·톤·분량·문체는 절대 바꾸지 마세요.\n"
    "맞춤법, 띄어쓰기, 명백한 오타만 고칩니다.\n"
    "출력은 교정된 본문만 작성하고, 설명·따옴표 없이 바로 본문을 시작하세요."
)


def proofread_text(text: str) -> str:
    body = text.strip()
    if not body:
        return text
    user = (
        "아래 생활기록부 문장의 맞춤법·띄어쓰기만 교정하세요. "
        "내용 추가·삭제·재작성은 하지 마세요.\n\n"
        f"{body}"
    )
    return generate_text(system=_SYSTEM, user=user, temperature=0.1, tier="fast")
