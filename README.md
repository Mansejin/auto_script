# auto_script

만세진 내부 자동화 저장소입니다. 크게 두 가지를 다룹니다.

| 구분 | 설명 |
|------|------|
| **디디딧 시트** | 유튜브 대본을 구글 시트에 반영하는 CLI + Cursor 에이전트 |
| **생기부 작성 머신** | 과거 생기부 샘플 학습 + 학생 데이터로 Gemini Pro 자동 작성 (CLI·관리자 웹) |

---

## 디디딧 시트 — 빠른 시작

### 1. Python 환경

```powershell
cd auto_script
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Windows에서는 `.\setup.ps1` 한 번으로 venv + 패키지 설치도 가능합니다.

### 2. Google 인증

**방법 A — OAuth (추천)**

1. [Google Cloud Console](https://console.cloud.google.com/)에서 **Google Sheets API**, **Google Drive API** 활성화
2. **OAuth 클라이언트 ID** (데스크톱) JSON → `credentials/oauth-client.json`
3. 최초 1회 로그인:

```powershell
python cli.py auth
```

`credentials/token.json`이 생성되면 본인 계정으로 접근 가능한 시트를 바로 씁니다.

**방법 B — 서비스 계정**

1. JSON → `credentials/service-account.json`
2. 시트를 서비스 계정 이메일에 **편집자**로 공유
3. `.env`에 `GOOGLE_AUTH_MODE=service_account`

### 3. 환경 변수

```powershell
copy config.example.env .env
```

`.env`에 `SPREADSHEET_ID`, 워크시트 이름을 설정하세요. 시트 ID는 구글 시트 URL의 `/d/` 와 `/edit` 사이 문자열입니다.

### 4. 시트 형식

열: **대본 | 장면 | 사이즈 | 자막 | 코멘트** — `장면` 값으로 파트(프롤로그, 디자인, 실사용 등)가 구분됩니다.

대본 작성 규칙: [`prompts/dididit.md`](prompts/dididit.md)

---

## Cursor에서 쓰는 방법

채팅에 수정 요청만 하면 CLI로 시트에 반영합니다. 제미나이 ↔ 시트를 직접 오갈 필요 없습니다.

| 요청 예시 | 동작 |
|-----------|------|
| "시트 현재 상태 보여줘" | `read` / `list-parts` |
| "15행 대본을 ~~로 바꿔줘" | `update` JSON 생성 후 반영 |
| "실사용 파트 전체를 이걸로 교체해줘" + 표 | `replace-part` |
| "제미나이 수정본이랑 뭐가 다른지 비교해줘" | `diff` 후 요약 |
| "수정본 시트에 반영해줘" | `apply` |

에이전트 규칙: [`.cursor/rules/dididit-sheet.mdc`](.cursor/rules/dididit-sheet.mdc)

---

## 디디딧 CLI 명령어

```powershell
python cli.py list-parts              # 파트 목록 (행 범위)
python cli.py read                    # 전체 읽기 (JSON)
python cli.py read --part 실사용      # 특정 파트만
python cli.py update changes/update.json
python cli.py replace-part "실사용" changes/new_part.tsv
python cli.py replace-range 20 45 changes/revised.tsv
python cli.py diff changes/revised.tsv --part 실사용
python cli.py apply changes/revised.tsv --part 실사용
```

### changes/ 폴더

수정용 임시 파일 (`changes/`는 git 제외):

- `changes/update.json` — 행 번호별 셀 수정
- `changes/revised.tsv` — 제미나이에서 받은 수정본 표

**update.json 예시**

```json
[
  {"row": 12, "대본": "수정된 한 줄 대사"},
  {"row": 18, "대본": "...", "자막": "핵심 스펙 요약"}
]
```

**TSV 예시** (탭 구분, 헤더 행 포함 가능)

```
대본	장면	사이즈	자막	코멘트
안녕하세요, 디디딧입니다.	프롤로그	미디엄		
```

---

## 생기부 작성 머신

고등학교 생활기록부를 **과거 샘플 패턴 학습 + 학생 데이터 + Gemini Pro**로 자동 작성합니다.

- 상세 사용법·배포: [`docs/saenggibu.md`](docs/saenggibu.md) (저장소 내부 문서)
- 관리자 웹·API URL은 공개 README에 적지 않습니다. 운영 환경은 `.env`와 배포 문서를 참고하세요.

```bash
pip install -r requirements.txt
cp config.example.env .env   # GEMINI_API_KEY, ADMIN_PASSWORD 등 설정

python sgb.py init
python sgb.py samples import data/saenggibu/examples/
python sgb.py analyze
python sgb.py students import data/saenggibu/examples/students.example.tsv
python sgb.py run --yes
```

NAS 자동 배포: [`docs/deploy-nas-auto.md`](docs/deploy-nas-auto.md)

---

## 보안 — Git에 올리면 안 되는 것

| 항목 | 위치 | 비고 |
|------|------|------|
| API 키 | `.env`, `GEMINI_API_KEY` | `config*.example.env`는 빈 값만 |
| 구글 인증 | `credentials/*.json` | `.gitignore` 처리됨 |
| 관리자 비밀번호 | `.env` `ADMIN_PASSWORD` | 코드·HTML에 힌트 넣지 말 것 |
| NAS SSH 비밀번호 | `config/nas-pc.local.env` | git 제외 |
| SSH 개인키 | 로컬 `~/.ssh/` | GitHub Secrets로만 CI에 전달 |

커밋 전 `git status`로 `.env`·`credentials/`가 스테이징되지 않았는지 확인하세요.

---

## 저장소 구조 (요약)

```
cli.py, src/          # 디디딧 시트 CLI
sgb.py, src/saenggibu/ # 생기부 작성 머신
server.py, web/admin/ # 관리자 웹 + API
scripts/              # NAS 배포·동기화 스크립트
docs/                 # 배포·운영 문서
prompts/dididit.md    # 대본 작성 규칙
```
