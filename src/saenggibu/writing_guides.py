from __future__ import annotations

from typing import Any

# 2026 기재요령·작성 실무에서 자주 걸리는 항목 요약 (인라인 가이드용)
WRITING_GUIDES: dict[str, dict[str, Any]] = {
    "common": {
        "title": "공통 (2026 기재요령 핵심)",
        "checklist": [
            "관찰된 사실·활동·태도만 기술 (추측·과장 금지)",
            "학생 실명 대신 「학생」「OO」 표기",
            "석차·등수·점수·평가 결과 미기재",
            "다른 학생과 비교·순위 표현 금지",
            "가정환경·사교육·외모·건강 민감정보 지양",
        ],
        "forbidden": ["1등", "최고", "석차", "90점", "학원", "부모 직업", "외모"],
    },
    "행발": {
        "title": "행동특성 및 종합의견",
        "checklist": [
            "학교생활 전반 태도·대인관계·책임감·성장",
            "강점 → 근거 사례 → 기대 순으로 연결",
            "500~700자 내외 (샘플 분석값 우선)",
            "명사형·서술형 종결 일관 유지",
        ],
        "forbidden": ["평가적 형용사 남발", "허위·과장", "특정 정치·종교 견해"],
    },
    "세특": {
        "title": "세부능력 및 특기사항",
        "checklist": [
            "해당 과목 수업·탐구·프로젝트·발표 등 구체 활동",
            "활동 → 참여 태도·역량 → 성장 포인트",
            "과목당 약 500자 (샘플·NEIS 한도 참고)",
            "비어 있는 진로·수행평가·주제는 본문에 언급하지 않음",
            "성취기준은 맥락 참고용 — 달성 단정 금지",
        ],
        "forbidden": ["점수·석차", "다른 과목 내용 혼입", "사실 없는 수상·대회"],
    },
    "창체": {
        "title": "창의적 체험활동",
        "checklist": [
            "자율·동아리·봉사·진로 영역별 분리",
            "활동명·역할·기여·배운 점",
            "영역당 150~300자 내외",
        ],
        "forbidden": ["영역 혼합 기재", "시간수·인증서 번호만 나열"],
    },
}

SECTION_ALIASES = {
    "자율": "창체",
    "동아리": "창체",
    "봉사": "창체",
    "진로": "창체",
}


def get_writing_guide(section: str | None = None) -> dict[str, Any]:
    if not section:
        return {"common": WRITING_GUIDES["common"], "sections": {k: v for k, v in WRITING_GUIDES.items() if k != "common"}}
    key = SECTION_ALIASES.get(section, section)
    guide = WRITING_GUIDES.get(key)
    if not guide:
        return {"common": WRITING_GUIDES["common"]}
    return {"common": WRITING_GUIDES["common"], "section": guide, "section_key": key}
