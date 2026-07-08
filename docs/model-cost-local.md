# Gemini 모델 정책

## 기본 동작

| 작업 | 모델 |
|------|------|
| **생기부 작성** (행발·세특·창체) | **3.1 Pro 고정** |
| **샘플 분석** (스타일 가이드 AI) | **3.1 Pro 고정** |
| **메모 파싱** 등 보조 | 2.5 Flash |

상세 편집의 **다시 쓰기·맞춤법** 기능은 없습니다. 본문은 직접 수정 후 저장하세요.

## 환경 변수

```env
GEMINI_MODEL=gemini-3.1-pro-preview
GEMINI_MODEL_FAST=gemini-2.5-flash
```

## 로컬 확인

```bash
python3 scripts/model_compare.py plan
python3 scripts/model_compare.py run --section 행발
```
