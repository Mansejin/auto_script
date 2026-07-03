# 로컬 테스트 (NAS 배포 전)

NAS에 배포할 때마다 Docker 컨테이너가 재시작되므로, **UI·기능 수정은 PC에서 먼저 확인**하고 NAS 배포는 하루 1~2회 정도만 하는 것을 권장합니다.

## 빠른 시작 (Windows)

```bat
scripts\DEV-로컬테스트.bat
```

또는 PowerShell:

```powershell
.\scripts\dev-local.ps1
```

브라우저에서 열기: **http://127.0.0.1:8787/admin/saenggibu**

## Mac / Linux

```bash
chmod +x scripts/dev-local.sh
./scripts/dev-local.sh
```

## 사전 준비

1. `.env` 파일 (없으면 스크립트가 `config.example.env`에서 복사)
2. 필수 값:
   - `ADMIN_PASSWORD` — 관리자 로그인 비밀번호
   - `GEMINI_API_KEY` — AI 분석·작성용 (없으면 업로드만 가능)

## 무엇이 로컬에서 되나요?

| 작업 | 로컬 반영 방법 |
|------|----------------|
| `web/admin/` HTML·CSS·JS | 저장 후 **Ctrl+F5** |
| `src/` Python API | **자동 재시작** (`SGB_RELOAD=1`) |
| `data/saenggibu/` 샘플·학생 데이터 | 로컬 `data/` 폴더 사용 (NAS와 별개) |

## NAS와 데이터

로컬 `data/saenggibu/`와 NAS 데이터는 **분리**됩니다. NAS 실제 샘플로 테스트하려면 SMB로 `data/saenggibu`를 복사하거나, 로컬에서 새로 업로드하세요.

## 배포 시점

- UI·버튼·문구 수정 → 로컬 확인 후 NAS 배포
- NAS docker-compose는 `web/admin`을 볼륨 마운트하므로, **UI만 바꾼 경우** 재배포 없이 SMB 동기화 + 새로고침으로도 반영 가능
- **Python API 변경**은 NAS에서 docker 재시작(배포) 필요

## 무제한 작성

로컬·NAS 모두 `SGB_PLAN=admin`이면 월 작성 횟수 제한이 없습니다 (`docker-compose.yml` 기본값).
