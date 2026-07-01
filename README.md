# auto_script

디디딧 대본 → 구글 시트 자동 반영 도구입니다. 제미나이에서 받은 수정 대본을 **Cursor 채팅에서 말하면 구글 시트에 자동 반영**할 수 있습니다.

## 빠른 시작

### 1. Python 환경

```powershell
cd c:\Users\Ohola\Desktop\project\auto_script
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

또는 Windows에서:

```powershell
.\setup.ps1
```

### 2. Google 인증 설정

**방법 A — OAuth (추천, 지금 만드신 파일)**

1. [Google Cloud Console](https://console.cloud.google.com/) → **API 및 서비스** → **라이브러리**에서 **Google Sheets API**, **Google Drive API** 활성화
2. **사용자 인증 정보** → **OAuth 클라이언트 ID** → 앱 유형 **데스크톱** → JSON 다운로드
3. JSON을 `credentials/oauth-client.json`에 저장
4. 최초 1회 로그인:

```powershell
python cli.py auth
```

브라우저에서 본인 구글 계정으로 로그인하면 `credentials/token.json`이 생성됩니다. 시트를 별도로 공유할 필요 없이 **본인 계정으로 접근 가능한 시트**를 바로 쓸 수 있습니다.

**방법 B — 서비스 계정**

1. 서비스 계정 JSON을 `credentials/service-account.json`에 저장
2. 구글 시트를 서비스 계정 이메일에 **편집자**로 공유
3. `.env`에서 `GOOGLE_AUTH_MODE=service_account` 설정

### 3. 환경 변수

```powershell
copy config.example.env .env
```

`.env`에서 시트 ID와 워크시트 이름을 확인하세요. (기본값은 디디딧 시트)

---

## Cursor에서 쓰는 방법

채팅에 이렇게 말하면 됩니다:

| 요청 예시 | 동작 |
|-----------|------|
| "시트 현재 상태 보여줘" | `read` / `list-parts` |
| "15행 대본을 ~~로 바꿔줘" | `update` JSON 생성 후 반영 |
| "실사용 파트 전체를 이걸로 교체해줘" + 표 붙여넣기 | `replace-part` |
| "제미나이 수정본이랑 뭐가 다른지 비교해줘" | `diff` 후 요약 |
| "수정본 시트에 반영해줘" | `apply` |

**제미나이 ↔ 시트 왕복 없이** 여기서 수정 요청만 하면 됩니다.

---

## CLI 명령어

```powershell
# 파트 목록 (행 범위)
python cli.py list-parts

# 전체 읽기 (JSON)
python cli.py read

# 특정 파트만
python cli.py read --part 실사용

# 행 단위 수정
python cli.py update changes/update.json

# 파트 전체 교체 (TSV/표 파일)
python cli.py replace-part "실사용" changes/new_part.tsv

# 행 범위 교체
python cli.py replace-range 20 45 changes/revised.tsv

# diff (변경점만 확인)
python cli.py diff changes/revised.tsv --part 실사용

# diff 후 자동 반영 (행 수 동일할 때)
python cli.py apply changes/revised.tsv --part 실사용
```

---

## changes/ 폴더

수정용 임시 파일을 `changes/`에 두세요. (git 제외)

- `changes/update.json` — 행 번호별 셀 수정
- `changes/revised.tsv` — 제미나이에서 받은 수정본 표

### update.json 예시

```json
[
  {"row": 12, "대본": "수정된 한 줄 대사"},
  {"row": 18, "대본": "...", "자막": "핵심 스펙 요약"}
]
```

### TSV 예시 (탭으로 구분)

```
대본	장면	사이즈	자막	코멘트
안녕하세요, 디디딧입니다.	프롤로그	미디엄		
```

---

## 시트 링크

https://docs.google.com/spreadsheets/d/19XxPdDT3ezxriN5hVgXUZ4z4dYxIxU-fNblS1pOtR0A/edit

열 구성: **대본 | 장면 | 사이즈 | 자막 | 코멘트**

대본 작성 규칙은 `prompts/dididit.md` 참고.
