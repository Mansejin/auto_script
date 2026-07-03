# 공유기(ipTIME) 없이 밖에서 나스 생기부 API 쓰기

집 **ipTIME에 로그인할 수 없어도** 됩니다.  
나스가 **밖으로 먼저 연결**하는 방식을 쓰면 포트포워딩이 필요 없습니다.

---

## 선택지 비교

| 방법 | ipTIME 필요 | 난이도 | mansejin.com 연동 |
|------|-------------|--------|-------------------|
| **Tailscale** (추천) | ❌ | ★★☆ | 스튜디오·집 PC에서 직접 접속 |
| **Cloudflare Tunnel** | ❌ | ★★★ | 공개 HTTPS URL 가능 |
| 포트포워딩 8787 | ✅ 집에서만 | ★★☆ | `ohola.synology.me:8787` |

스튜디오에서 **지금 당장** 쓰려면 → **Tailscale**  
나중에 **mansejin.com**에서도 쓰려면 → **Cloudflare Tunnel** 또는 집에 가서 ipTIME 설정

---

## 방법 1: Tailscale (추천, 15분)

집 PC·스튜디오 PC·나스만 **비밀 VPN**으로 묶습니다. 공유기 설정 0.

### 1) Tailscale 계정

https://tailscale.com → Google 등으로 무료 가입

### 2) 나스에 설치 (DSM `5012`로 지금 설정 가능)

**A. 패키지 센터에 Tailscale 있으면**

1. `https://ohola.synology.me:5012/` 로그인
2. **패키지 센터** → **Tailscale** 설치
3. Tailscale 앱 열기 → 계정 로그인
4. **Enable** / 연결 승인

**B. 없으면 Docker로**

Container Manager → **레지스트리** → `tailscale/tailscale` 검색 → 다운로드  
(고급 사용자용. 패키지가 있으면 A가 쉬움.)

### 3) 스튜디오 PC에 설치

https://tailscale.com/download/windows → 설치 → **같은 계정** 로그인

### 4) 나스 Tailscale IP 확인

1. DSM Tailscale 화면 또는 https://login.tailscale.com/admin/machines
2. 나스 기기 옆 IP 확인 (예: `100.101.102.103`)

### 5) 생기부 접속 (스튜디오에서)

먼저 Container Manager에서 `saenggibu-api` **실행 중**인지 확인.

```
http://100.101.102.103:8787/admin/saenggibu
```

(Tailscale IP는 기기마다 다름, `https` 아님)

health 확인:

```
http://100.101.102.103:8787/health
```

> Tailscale 켜진 PC/폰에서만 접속됩니다. URL을 아는 다른 사람은 접속 불가 → **관리자용으로 적합**

### 6) mansejin.com 연동 (선택)

Tailscale IP는 외부 웹(mansejin.com)에서 **직접 호출 불가**.  
스튜디오에서는 Tailscale 주소로 쓰고, mansejin 연동은 Cloudflare Tunnel 또는 집에서 ipTIME 설정 후 진행.

---

## 방법 2: Cloudflare Tunnel (공개 HTTPS, ipTIME 불필요)

나스 Docker에 `cloudflared`를 띄우면 `https://xxxx` 주소가 생깁니다.

1. Cloudflare 무료 계정 + 도메인(선택)
2. Container Manager에서 cloudflared 컨테이너 추가
3. 터널이 `localhost:8787`로 연결
4. 발급된 URL을 `data-api-base`에 설정

설정이 Tailscale보다 길어서, 필요하면 별도 요청 시 단계별로 적어 드립니다.

---

## 방법 3: 집에 갈 때 ipTIME (한 번만)

집에 가면 공유기 관리 페이지 (보통 `192.168.0.1` 또는 `192.168.1.1`):

- 외부 8787 → 시놀로지 IP 8787 (5012 했던 것과 동일)

이후 `http://ohola.synology.me:8787/admin/saenggibu`

---

## 지금 스튜디오에서 할 일 (순서)

```
1. https://ohola.synology.me:5012/  DSM 로그인
2. Container Manager → saenggibu 실행 확인
3. Tailscale 나스 + 스튜디오 PC 설치 (같은 계정)
4. http://[나스-Tailscale-IP]:8787/admin/saenggibu 접속
```

ipTIME은 **안 건드려도 됩니다.**

---

## 자주 묻는 것

**Q. Tailscale IP가 뭔지 모르겠어요**  
→ https://login.tailscale.com/admin/machines 에서 `ohola` / Synology 이름 찾기

**Q. health는 되는데 로그인이 안 돼요**  
→ `.env`의 `ADMIN_PASSWORD` 확인

**Q. mansejin.com/admin/saenggibu 에서는 여전히 안 돼요**  
→ 정상. mansejin은 공개 인터넷용이라 Tailscale만으로는 안 됨. Tunnel 또는 ipTIME 필요
