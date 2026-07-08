# Gemini 모델·비용 로컬 실험

라이브(NAS) 서버 설정을 바꾸지 않고, 로컬에서만 토큰 비용·품질 트레이드오프를 비교하는 방법입니다.

## 빠른 시작

```bash
cp config.local.example.env .env.local
# .env.local 에 GEMINI_API_KEY 설정

# 호출 계획만 보기 (API 키 불필요)
python3 scripts/model_compare.py plan

# 실제 1회 생성 (키 필요)
python3 scripts/model_compare.py run --profile split --section 행발
python3 scripts/model_compare.py run --profile flash --section 행발

# 관리자 UI 로컬 서버 (.env + .env.local 자동 로드)
./scripts/dev-local.sh
```

`.env.local`은 `.env`보다 우선합니다. NAS `.env`는 그대로 두고 로컬만 실험할 수 있습니다.

## 모델 프로필 (`GEMINI_MODEL_PROFILE`)

| 프로필 | 동작 | 비용 | 품질 |
|--------|------|------|------|
| **split** (기본·권장) | 작성·샘플분석=Pro, 맞춤법·편집·파싱=Flash | 중간 | 최적 균형 |
| **flash** | 모든 Gemini 호출을 Flash | 약 5~10× 저렴 | 행발·세특·창체 문체·사실성 하락 가능 |
| **pro** | 모든 호출을 Pro | 최고 | 품질 최대, 비용 최대 |

### 전부 Flash로 바꾸면 퀄리티가 많이 떨어질까?

**보조 작업**(맞춤법, 분량 조절, 검사 지적 수정, 메모 파싱)은 Flash로 충분합니다. 이미 `split` 프로필이 이렇게 동작합니다.

**본문 작성**(행발·세특·창체)을 Flash로 내리면:

- 스타일 가이드·관찰 중심 문체 준수가 약해질 수 있음
- 과장·평가적 표현, 사실 왜곡이 늘 수 있음
- 분량·형식은 대체로 맞지만 “교사 손맛”이 줄어듦

**권장:** 운영은 `split` 유지. 비용이 급하면 `GEMINI_SKIP_PROOFREAD=1`로 작성 후 자동 맞춤법 1회를 먼저 끄고, 그래도 부족하면 `flash`를 로컬에서 A/B 비교 후 검토.

## 추가 절감 (`GEMINI_SKIP_PROOFREAD`)

필드 1개당 API 호출이 **2회 → 1회**로 줄어듭니다 (작성 + 맞춤법 중 맞춤법 생략).

- 일괄 작성(`generator`)과 필드 재생성(`regenerate`) 모두 적용
- 수동 “맞춤법” 버튼은 그대로 동작
- 띄어쓰기·오탈자가 소폭 늘 수 있음

## 학생 1명·행발 1필드 기준 호출 수

| 설정 | 호출 수 | 모델 |
|------|---------|------|
| split | 2 | Pro + Flash |
| split + SKIP_PROOFREAD | 1 | Pro |
| flash | 2 | Flash + Flash |
| flash + SKIP_PROOFREAD | 1 | Flash |
| pro | 2 | Pro + Pro |

세특은 과목마다 위와 동일하게 반복됩니다.

## model_compare.py 명령

```bash
python3 scripts/model_compare.py info
python3 scripts/model_compare.py plan --profiles split,flash,pro --section 세특 --subjects 3
python3 scripts/model_compare.py plan --skip-proofread
python3 scripts/model_compare.py run --profile flash --section 행발 --skip-proofread
python3 scripts/model_compare.py run --profile split --section 행발 --json
```

`run` 실행 후 **입력(prompt)·출력(candidates)·합계 토큰**이 출력됩니다. Google API `usage_metadata` 기준이며, 청구 금액과 1:1은 아닐 수 있습니다.

벤치마크 학생 데이터: `data/saenggibu/fixtures/benchmark_student.json`

## NAS 배포 시

- `GEMINI_MODEL_PROFILE`, `GEMINI_SKIP_PROOFREAD`는 **로컬 검증 후** NAS `.env`에만 반영
- `.env.local`은 배포 대상 아님 (gitignore 권장)
- API 동작 변경 시 `sh scripts/nas-docker-update.sh --full-build`
