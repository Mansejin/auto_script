# 로컬 테스트 (NAS 배포 전)

NAS에 배포할 때 **매번** 컨테이너·터널을 재시작할 필요는 없습니다. `nas-docker-update.sh`가 변경 파일을 보고 자동으로 판단합니다.

| 변경 내용 | 필요한 작업 |
|-----------|-------------|
| `web/admin` (HTML·CSS·JS) | **git pull만** — 볼륨 마운트라 재시작 불필요. 브라우저 **Ctrl+F5** |
| `src/` Python API | API **rebuild** (이미지 재빌드 — restart만으로는 코드 반영 안 됨) |
| `Dockerfile`, `requirements.txt`, compose | API **rebuild** |
| Cloudflare 터널 | **거의 재시작 안 함** (터널 설정 바뀔 때만) |

수동 옵션:

```bash
sh scripts/nas-docker-update.sh --pull-only   # git만
sh scripts/nas-docker-update.sh --no-build      # git + docker 스킵
sh scripts/nas-docker-update.sh --full-build    # 항상 API 재빌드
```

Windows: `scripts\NAS-업데이트-API.bat` — Python·맞춤법 검사 등 API 변경 반영 시 사용.

UI만 급히 반영: `NAS-UI-동기화.bat` (SMB 복사) 또는 git pull 후 Ctrl+F5.

**UI·기능 수정은 PC에서 먼저 확인**하고 NAS 배포는 하루 1~2회 정도만 하는 것을 권장합니다.

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

의존성 오류(`No module named 'dotenv'`) 시 먼저:
```bat
scripts\DEV-의존성설치.bat
```

3. 검은 창에 `Application startup complete` 또는 `Uvicorn running` 이 보이고 **에러 traceback 이 없어야** 합니다.
### 4) 브라우저 접속 + 로그인

- http://127.0.0.1:8787/admin/saenggibu
- **로컬 기본 비밀번호:** `dev-local` (`.env` 의 `ADMIN_PASSWORD`)

NAS/운영 서버는 `.env` 에 본인 비밀번호를 직접 설정하세요.

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
| `ModuleNotFoundError: dotenv` 등 | `scripts\DEV-의존성설치.bat` 실행 후 재시작 |
| `DEV-로컬테스트.bat` 없음 | `git pull` 후 `scripts\` 폴더 확인 |
| 포트 사용 중 | `dev-local.ps1 -Port 8788` 로 다른 포트 사용 |
| 로그인 안 됨 | 로컬: 비밀번호 **`dev-local`** / `.env` 에 `ADMIN_PASSWORD`·`ADMIN_SESSION_SECRET` 확인 후 서버 재시작 |

**서버만 켜져 있는지 확인:** http://127.0.0.1:8787/health → `{"status":"ok"}`

### Python 9009 (Windows 흔한 오류)

`python`이 설치된 것처럼 보이지만 실제로는 **Microsoft Store 링크**인 경우입니다.

1. **설정** → **앱** → **고급 앱 설정** → **앱 실행 별칭**
2. **python.exe**, **python3.exe** 를 **끔**
3. https://www.python.org/downloads/ 에서 Python 3.10+ 설치 (**Add to PATH** 체크)
4. **새** PowerShell 열고 확인:
   ```powershell
   py -3 --version
   ```
5. `scripts\DEV-Python확인.bat` 실행 후 `DEV-로컬테스트.bat` 재실행
