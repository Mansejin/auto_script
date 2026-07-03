# 로컬 테스트 (NAS 배포 전)

NAS에 배포할 때마다 Docker 컨테이너가 재시작되므로, **UI·기능 수정은 PC에서 먼저 확인**하고 NAS 배포는 하루 1~2회 정도만 하는 것을 권장합니다.

## 빠른 시작 (Windows)

1. **먼저** 저장소 최신 받기:
```powershell
cd C:\Users\Ohola\Documents\GitHub\auto_script
git pull
```

2. **서버 실행** (탐색기 더블클릭 또는):
```bat
scripts\DEV-로컬테스트.bat
```

3. 검은 창이 떠 있고 `Uvicorn running on http://127.0.0.1:8787` 가 보여야 합니다.  
   **이 창을 닫으면 접속이 안 됩니다.**

4. 브라우저: **http://127.0.0.1:8787/admin/saenggibu**

또는 PowerShell:

```powershell
.\scripts\dev-local.ps1
```

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

## 접속 안 될 때

| 증상 | 확인 |
|------|------|
| 연결할 수 없음 / ERR_CONNECTION_REFUSED | **서버 창이 켜져 있는지** 확인. bat 실행 후 창이 바로 닫히면 Python 미설치·오류 |
| `DEV-로컬테스트.bat` 없음 | `git pull` 후 `scripts\` 폴더 확인 |
| Python not found | [python.org](https://www.python.org/downloads/) 설치, **Add to PATH** 체크, 터미널 재시작 |
| 포트 사용 중 | `dev-local.ps1 -Port 8788` 로 다른 포트 사용 |
| 로그인 안 됨 | `.env` 의 `ADMIN_PASSWORD=` 값 설정 후 서버 재시작 |

**서버만 켜져 있는지 확인:** 브라우저에서 http://127.0.0.1:8787/health → `{"status":"ok"}` 나오면 정상.
