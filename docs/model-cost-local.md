# Gemini 모델 정책

## 기본 동작

| 작업 | 모델 |
|------|------|
| **샘플 분석** (스타일 가이드 AI 정리) | **3.1 Pro 고정** |
| **일괄 작성** (④ 작성) | **2.5 Flash 기본** |
| **맞춤법** (수동 버튼) | 2.5 Flash |
| **다시 쓰기** (상세 편집) | 사용자 선택: 2.5 Flash / 3.1 Pro |

자동 맞춤법(작성 직후 1회)은 **없음**.

## 환경 변수

```env
GEMINI_MODEL=gemini-3.1-pro-preview      # 샘플 분석·Pro 다시 쓰기
GEMINI_MODEL_FAST=gemini-2.5-flash     # 일괄 작성·맞춤법 기본
```

## 로컬 비교

```bash
python3 scripts/model_compare.py plan
python3 scripts/model_compare.py run --tier fast --section 행발
python3 scripts/model_compare.py run --tier pro --section 행발
```

## 품질이 안 나올 때

일괄 작성(Flash) 결과가 마음에 안 들면 → 상세 편집에서 **모델을 3.1 Pro로 바꾼 뒤 다시 쓰기**.
