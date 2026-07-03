# NAS에 생기부 API 배포하기

집에 **나스(NAS)** 가 있으면 Railway·Cloudflare Tunnel 없이 **24시간 돌릴 수 있습니다.**  
PC를 켜 둘 필요 없고, 학생 데이터도 나스 디스크에 저장됩니다.

대부분 **시놀로지(Synology)** 또는 **QNAP** 기준으로 적었습니다.

> **시놀로지 + Container Manager** → [`docs/deploy-synology.md`](deploy-synology.md) (화면별 클릭 가이드)

---

## 전체 그림

```
[mansejin.com/admin/saenggibu]  ← 관리자 화면 (GitHub Pages)
            ↓ HTTPS
[나스 역방향 프록시]  sgb.mansejin.com
            ↓
[Docker 컨테이너]  saenggibu-api :8787
            ↓
[data/saenggibu/]  학생·샘플·작성 결과 (나스 폴더)
```

---

## 준비물

- [ ] 나스에 **Docker**(시놀로지: Container Manager) 설치됨
- [ ] `auto_script` 프로젝트를 나스에 둘 폴더 (예: `/docker/saenggibu/`)
- [ ] Gemini API 키
- [ ] `mansejin.com` DNS를 나스 IP로 연결할 방법 (역방향 프록시 + HTTPS)

---

## 1단계: 프로젝트를 나스에 올리기

### 방법 A — Git (추천)

나스 SSH 접속 후:

```bash
cd /volume1/docker   # 시놀로지 예시. QNAP은 /share/Container 등
git clone https://github.com/Mansejin/auto_script.git saenggibu
cd saenggibu
git checkout cursor/saenggibu-writer-5821   # 또는 main 머지 후
```

### 방법 B — ZIP 업로드

PC에서 프로젝트 폼더를 압축 → 나스 **File Station**으로 `docker/saenggibu/` 에 업로드 후 풀기

---

## 2단계: .env 만들기

나스에서:

```bash
cd /volume1/docker/saenggibu
cp config.nas.example.env .env
nano .env   # 또는 File Station에서 메모장으로 편집
```

**꼭 채울 것:**

```env
GEMINI_API_KEY=제미나이_키
ADMIN_PASSWORD=관리자비밀번호
ADMIN_SESSION_SECRET=랜덤긴문자열32자이상
SGB_ALLOWED_ORIGINS=https://mansejin.com,https://www.mansejin.com
```

---

## 3단계: Docker로 실행

SSH에서 프로젝트 폴더 안:

```bash
docker compose up -d --build
```

또는 **시놀로지 Container Manager**:

1. **프로젝트** → **생성** → `docker-compose.yml` 있는 폴더 선택
2. 빌드 후 **실행**

### 동작 확인 (나스 안에서)

```bash
curl http://127.0.0.1:8787/health
```

`{"status":"ok"}` 나오면 성공.

같은 와이파이 폰/PC에서 `http://나스IP:8787/admin/saenggibu` 로도 열어 볼 수 있습니다.

---

## 4단계: HTTPS 주소 만들기 (역방향 프록시)

mansejin.com 페이지는 **HTTPS** API만 호출할 수 있어서, 나스 앞에 **주소 하나**를 달아야 합니다.

예: `https://sgb.mansejin.com` → 나스 `localhost:8787`

### 시놀로지

1. **제어판** → **로그인 포털** → **고급** → **역방향 프록시**
2. **생성**
   - 소스: `sgb.mansejin.com`, HTTPS, 포트 443
   - 대상: `localhost`, HTTP, 포트 `8787`
3. **제어판** → **보안** → **인증서** → Let's Encrypt로 `sgb.mansejin.com` 발급 (또는 와일드카드 `*.mansejin.com`)

### QNAP

1. **myQNAPcloud** 또는 **SSL Certificate**
2. **Web Server** / **Reverse Proxy** 에서 위와 같이 `sgb.mansejin.com` → `127.0.0.1:8787`

### DNS

도메인 관리(DNS)에서:

```
sgb.mansejin.com  →  A레코드  →  집 공인 IP
```

(공인 IP가 바뀌면 DDNS 사용 — 시놀로지/QNAP 기본 제공)

### 공유기

443 포트를 **나스 IP**로 포워딩 (이미 나스 HTTPS 쓰고 있으면 설정돼 있을 수 있음)

---

## 5단계: mansejin.com 관리자 페이지 연결

`tools-site`의 `admin/saenggibu/index.html`:

```html
<body data-api-base="https://sgb.mansejin.com">
```

`deploy/tools-site-admin/` 내용을 tools-site에 반영 후 push.

접속: **https://mansejin.com/admin/saenggibu/**  
→ 비밀번호 로그인 → 학생 목록이 보이면 **완료**.

---

## 데이터는 어디에?

나스 폴더 `data/saenggibu/` (docker-compose 볼륨):

| 폴더/파일 | 내용 |
|-----------|------|
| `students/` | 학생 정보 |
| `samples/` | 과거 생기부 샘플 |
| `patterns.json` | 문체 패턴 |
| `outputs/` | 작성 결과 백업 |

**나스 백업**에 이 폴더만 포함되면 학생 데이터도 같이 백업됩니다.

---

## 자주 쓰는 명령

```bash
cd /volume1/docker/saenggibu

docker compose logs -f          # 로그 보기
docker compose restart          # 재시작
docker compose down             # 중지
docker compose up -d --build    # 코드 업데이트 후 재빌드
```

---

## 보안 체크

1. **8787 포트를 인터넷에 직접 열지 말 것** — 역방향 프록시(443)만 쓰기
2. `.env`는 나스에만 두고 GitHub에 올리지 말 것
3. `ADMIN_PASSWORD` 강하게 설정
4. 관리자 URL(`mansejin.com/admin/saenggibu`) 공개하지 말 것

---

## 문제 해결

| 증상 | 확인 |
|------|------|
| 컨테이너가 바로 꺼짐 | `docker compose logs` → `.env` 누락 여부 |
| mansejin에서 로그인 실패 | `ADMIN_PASSWORD`, `data-api-base` 주소 |
| CORS 오류 | `.env`의 `SGB_ALLOWED_ORIGINS`에 `https://mansejin.com` |
| 작성만 실패 | `GEMINI_API_KEY` |
| HTTPS 인증서 오류 | 역방향 프록시에 인증서 연결 여부 |

---

## 요약 — 당신이 할 일

```
1. 나스에 git clone (또는 폴더 업로드)
2. .env 3줄 채우기
3. docker compose up -d --build
4. 역방향 프록시로 sgb.mansejin.com → 8787
5. tools-site admin 페이지에 data-api-base 연결
6. https://mansejin.com/admin/saenggibu/ 로그인
```

나스가 **시놀로지인지 QNAP인지**, **Docker(Container Manager) 설치 여부** 알려주시면 그 화면 기준으로 더 짧게 적어 드리겠습니다.
