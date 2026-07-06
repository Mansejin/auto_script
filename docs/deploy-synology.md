# 시놀로지 NAS 배포 가이드 (Container Manager)

시놀로지 + Docker(Container Manager) 기준 **화면에서 누르는 순서**만 적었습니다.  
SSH 몰라도 됩니다. (SSH 쓰는 방법은 맨 아래 참고)

---

## 끝나면 이렇게 씁니다

| 접속 주소 | 용도 |
|-----------|------|
| `http://시놀로지IP:8787/admin/saenggibu` | 나스 안에서 테스트 |
| `https://sgb.mansejin.com/admin/saenggibu` | 역방향 프록시 설정 후 |
| `https://mansejin.com/admin/saenggibu/` | 최종 관리자 페이지 |

---

## 0. 미리 준비

- [ ] Gemini API 키: https://aistudio.google.com/apikey
- [ ] 관리자 비밀번호 (본인만 아는 것)
- [ ] 시놀로지 **File Station**, **Container Manager** 앱 설치됨

---

## 1. 파일 올리기 (File Station)

### 1-1. 폴더 만들기

1. 시놀로지 DSM 로그인
2. **File Station** 실행
3. `docker` 폴더 없으면 만들기 (공유 폴더 `docker` 또는 홈 아래 `docker`)
4. 그 안에 `saenggibu` 폴더 만들기

최종 경로 예시: `docker/saenggibu/`

### 1-2. 프로젝트 파일 넣기

**방법 A — PC에서 ZIP (SSH 없을 때 추천)**

1. PC에서 https://github.com/Mansejin/auto_script/archive/refs/heads/main.zip 다운로드
2. ZIP 풀기
3. 안에 있는 파일·폴더 전부를 File Station의 `docker/saenggibu/` 에 업로드

업로드 후 `docker/saenggibu/` 안에 이런 것들이 있어야 합니다:

```
docker-compose.yml
Dockerfile
server.py
sgb.py
requirements.txt
config.nas.example.env
src/
web/
...
```

**방법 B — SSH + git** (패키지 센터에서 SSH 활성화한 경우)

```bash
cd /volume1/docker
git clone https://github.com/Mansejin/auto_script.git saenggibu
cd saenggibu
git checkout main
```

---

## 2. .env 파일 만들기 (비밀 설정)

1. File Station → `docker/saenggibu/`
2. `config.nas.example.env` 우클릭 → **복사** → 이름을 `.env` 로 붙여넣기  
   (또는 PC 메모장으로 `config.nas.example.env` 열어서 저장 시 이름 `.env`, File Station 업로드)

3. `.env` 더블클릭 → **텍스트 편집기**로 열기

4. 아래만 채우고 **저장**:

```env
GEMINI_API_KEY=여기에_제미나이_키
ADMIN_PASSWORD=내관리자비밀번호
ADMIN_SESSION_SECRET=mansejin-sgb-아무랜덤긴문자열-2026
SGB_ALLOWED_ORIGINS=https://mansejin.com,https://www.mansejin.com
```

> `ADMIN_SESSION_SECRET`은 비밀번호랑 다른 아무 긴 문장이면 됩니다.

---

## 3. Container Manager로 실행

### 3-1. 프로젝트 생성 (DSM 7.2+ / Container Manager)

1. **Container Manager** 앱 실행
2. 왼쪽 **프로젝트** (Project) 클릭
3. **생성** (Create)
4. 설정:
   - **이름**: `saenggibu`
   - **경로**: `docker/saenggibu` 선택 (docker-compose.yml 있는 폴더)
5. **다음** → 웹 포털 설정은 **끄기** (우리가 8787 씀)
6. **완료** / **빌드** 후 **실행** (Start)

처음엔 이미지 빌드 때문에 **5~10분** 걸릴 수 있습니다.

### 3-2. 잘 돌아가는지 확인

1. Container Manager → **컨테이너**
2. `saenggibu-api` (또는 비슷한 이름) 상태가 **실행 중**인지 확인
3. PC/폰 브라우저 (같은 집 와이파이):

```
http://시놀로지IP:8787/health
```

`{"status":"ok"}` 가 보이면 성공.

4. 관리자 화면 테스트:

```
http://시놀로지IP:8787/admin/saenggibu
```

`.env`에 적은 `ADMIN_PASSWORD`로 로그인 → 탭이 보이면 **API 완료**.

### 3-3. 컨테이너가 바로 꺼질 때

1. Container Manager → 해당 컨테이너 → **세부 정보** → **로그**
2. 대부분 `.env` 없음 / `GEMINI_API_KEY`·`ADMIN_PASSWORD` 비어 있음
3. File Station에서 `.env` 위치·내용 다시 확인 후 프로젝트 **재시작**

---

## 4. 밖에서 접속 — HTTPS 주소 만들기

mansejin.com 페이지는 **https** API만 호출합니다.  
`sgb.mansejin.com` 같은 주소를 나스에 연결합니다.

### 4-1. DDNS (집 IP가 바뀔 때)

이미 시놀로지 DDNS 쓰고 있으면 건너뛰어도 됩니다.

1. **제어판** → **외부 액세스** → **DDNS**
2. 서비스 추가 (Synology 제공 무료 DDNS 등)

### 4-2. DNS (도메인 관리 페이지)

`mansejin.com` DNS 관리에서 **A 레코드** 추가:

| 호스트 | 값 |
|--------|-----|
| `sgb` | 집 **공인 IP** (또는 DDNS가 가리키는 IP) |

몇 분~몇 시간 후 `sgb.mansejin.com`이 나스로 연결됩니다.

### 4-3. SSL 인증서 (Let's Encrypt)

1. **제어판** → **보안** → **인증서**
2. **추가** → **새 인증서 받기**
3. 도메인: `sgb.mansejin.com` 입력
4. 이메일·와일드카드 설정 후 발급

(이미 `*.mansejin.com` 인증서가 있으면 그걸 써도 됩니다)

### 4-4. 역방향 프록시

1. **제어판** → **로그인 포털** → **고급** → **역방향 프록시**
2. **생성**

**소스 (들어오는 요청)**

| 항목 | 값 |
|------|-----|
| 프로토콜 | HTTPS |
| 호스트 이름 | `sgb.mansejin.com` |
| 포트 | 443 |

**대상 (나스 안으로 보낼 곳)**

| 항목 | 값 |
|------|-----|
| 프로토콜 | HTTP |
| 호스트 이름 | `localhost` |
| 포트 | `8787` |

3. **사용자 지정 헤더** 탭 (있으면): 기본값 유지
4. **저장**

### 4-5. 공유기 포트

이미 시놀로지 HTTPS(443)를 쓰고 있으면 **추가 설정 없을 수 있습니다.**  
아니면 공유기에서 **443 → 시놀로지 IP** 포워딩.

> **8787 포트는 인터넷에 열지 마세요.** 443 역방향 프록시만 쓰면 됩니다.

### 4-6. HTTPS 확인

브라우저에서:

```
https://sgb.mansejin.com/health
```

`{"status":"ok"}` 나오면 역방향 프록시 성공.

---

## 5. mansejin.com 관리자 페이지 연결

`tools-site` 저장소의 `admin/saenggibu/index.html` (또는 `deploy/tools-site-admin/` 복사본):

```html
<body data-api-base="https://sgb.mansejin.com">
```

GitHub에 push → 몇 분 후:

**https://mansejin.com/admin/saenggibu/**

비밀번호 로그인 → 학생 목록 로드되면 **전부 끝**.

---

## 6. 데이터 백업

학생·샘플·작성 결과는 나스 폴더에 저장됩니다:

```
docker/saenggibu/data/saenggibu/
```

시놀로지 **Hyper Backup** 등에 `docker` 폴더 넣어 두면 같이 백업됩니다.

---

## 자주 쓰는 것 (Container Manager)

| 하고 싶은 것 | 방법 |
|--------------|------|
| 재시작 | 프로젝트 `saenggibu` → **작업** → **다시 시작** |
| 로그 보기 | 컨테이너 → **세부 정보** → **로그** |
| 코드 업데이트 | File Station에 새 파일 덮어쓰기 → 프로젝트 **다시 빌드** |
| 끄기 | 프로젝트 **중지** |

---

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| 프로젝트 생성 시 오류 | `docker-compose.yml` 있는 폴더 맞는지, `.env` 있는지 | |
| 8787 접속 안 됨 | 컨테이너 미실행 / 포트 미개방 | 아래 **「8787 안 될 때」** 참고 |
| `https://...:8787` 안 됨 | **8787은 HTTP 전용** (SSL 없음) | `http://` 로 접속 |
| mansejin 로그인 안 됨 | `ADMIN_PASSWORD`, `data-api-base` 주소 확인 | |
| 로그인은 되는데 목록 안 뜸 | 브라우저 F12 → Console에 CORS 오류면 `.env`에 `SGB_ALLOWED_ORIGINS` 확인 | |
| 작성만 실패 | `GEMINI_API_KEY` 확인 | |
| sgb.mansejin.com 인증서 오류 | 제어판 인증서 + 역방향 프록시 호스트 이름 일치 | |

### 「8787 안 될 때」— ohola.synology.me 포함

**IP를 몰라도 됩니다.** `ohola.synology.me`가 시놀로지 주소입니다.  
다만 아래를 **순서대로** 확인하세요.

#### ① `https` 가 아니라 `http` 로

우리 API 서버는 **8787에서 HTTPS(SSL)를 쓰지 않습니다.**

```
❌ https://ohola.synology.me:8787/admin/saenggibu
✅ http://ohola.synology.me:8787/admin/saenggibu
```

브라우저가 "안전하지 않음" 경고를 띄울 수 있는데, **집 안에서 테스트할 때는 진행**해도 됩니다.

#### ② 컨테이너가 실제로 돌아가는지

1. **Container Manager** → **컨테이너**
2. `saenggibu-api` 상태가 **실행 중**인지
3. 꺼져 있으면 → **프로젝트** `saenggibu` → **시작**
4. 바로 꺼지면 → 컨테이너 **로그** 확인 (대부분 `.env` 누락)

#### ③ 집 안(같은 와이파이)에서 먼저 테스트

외부 인터넷보다 **집 안**이 먼저입니다.

```
http://ohola.synology.me:8787/health
```

`{"status":"ok"}` 가 보여야 합니다.

**시놀로지 IP 찾는 법** (로컬 테스트용, 몰라도 DDNS로 가능):

1. DSM 로그인 화면 주소창에 `find.synology.com` 또는 이미 쓰는 `ohola.synology.me:5000`
2. **제어판** → **네트워크** → **네트워크 인터페이스** → **LAN** → IPv4 주소  
   예: `192.168.0.15`
3. 그때는 `http://192.168.0.15:8787/health` 로도 동일하게 테스트

#### ④ 집 안에서는 되는데 밖( LTE·학교·스튜디오 )에서는 안 됨

**`연결을 거부했습니다` / `ERR_CONNECTION_REFUSED`** → 정상적인 상황일 수 있습니다.

나스는 **집 안**에 있고, 스튜디오 와이파이는 **밖(인터넷)** 입니다.  
아직 **집 공유기 → 나스 8787** 이 열려 있지 않으면 밖에서는 **절대** 접속되지 않습니다.

| 위치 | `http://ohola.synology.me:8787` |
|------|----------------------------------|
| 집 와이파이 | 설정 전에도 될 수 있음 (컨테이너만 실행 중이면) |
| 스튜디오·학교·LTE | **역방향 프록시 또는 포트포워딩 설정 후에만** 가능 |

**지금 스튜디오에서 할 일**

1. **집에 가서** (또는 집 DSM에 원격 접속되면 그때) 아래 ⑤ 역방향 프록시 설정
2. 그 전까지는 **집 와이파이**에서만 `http://ohola.synology.me:8787` 로 테스트

**집 DSM에 스튜디오에서 접속되는지 확인**

브라우저에서 (시놀로지 기본 포트):

```
https://ohola.synology.me:5001
```

또는 QuickConnect 주소로 DSM 로그인이 되면, **집에 안 가도** Container Manager·역방향 프록시 설정 가능합니다.

**방법 A — 역방향 프록시 (추천, 443만 사용)**

1. **제어판** → **로그인 포털** → **고급** → **역방향 프록시** → **생성**
2. 소스: `sgb.ohola.synology.me` (또는 `ohola.synology.me`) HTTPS **443**
3. 대상: `localhost` HTTP **8787**
4. **제어판** → **외부 액세스** → **DDNS**에서 `sgb` 서브도메인 추가 가능한지 확인
5. 접속: `https://sgb.ohola.synology.me/admin/saenggibu`

mansejin 페이지 `data-api-base`도 이 HTTPS 주소로 변경.

**방법 B — 공유기에서 8787 포트 포워딩**

- 공유기 관리 페이지 → 포트포워딩 → 외부 8787 → 시놀로지 IP 8787  
- 보안상 **A를 권장**

#### ⑤ 방화벽

**제어판** → **보안** → **방화벽** 사용 중이면 **8787 허용** 규칙 추가 (로컬 테스트용).

---

## SSH로 하고 싶을 때만

```bash
cd /volume1/docker/saenggibu
sudo docker compose up -d --build
sudo docker compose logs -f
sudo docker compose restart
```

---

## 체크리스트 (출력해서 쓰기)

```
□ docker/saenggibu/ 에 파일 업로드
□ .env 에 키 3개 입력
□ Container Manager 프로젝트 생성·실행
□ http://시놀로지IP:8787/admin/saenggibu 로그인 성공
□ DNS sgb.mansejin.com → 공인 IP
□ 역방향 프록시 sgb.mansejin.com → localhost:8787
□ https://sgb.mansejin.com/health OK
□ tools-site data-api-base 연결
□ https://mansejin.com/admin/saenggibu/ 최종 확인
```

막히는 **체크리스트 번호**만 알려주시면 그 단계만 더 짧게 도와드리겠습니다.
