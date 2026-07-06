# 점검 중 페이지

배포·재시작 중 Cloudflare **502 Bad Gateway** 대신 **점검 중** 안내를 보여 줍니다.

## 동작 방식

1. **Nginx 게이트웨이** (`sgb-gateway`)가 8787 포트를 받습니다.
2. API(`sgb-api`)가 잠깐 내려가면 게이트웨이가 `web/maintenance.html`을 반환합니다.
3. `nas-docker-update.sh` 실행 시 `data/saenggibu/maintenance.on` 파일을 만들어, 재빌드 전부터 점검 페이지를 띄웁니다.
4. 헬스체크 성공 후 `maintenance.on`을 지웁니다.

## 최초 1회 (이미 배포 중인 NAS)

### 1) 코드 반영

`NAS-업데이트.bat` 또는 `nas-docker-update.sh`로 최신 `main`을 받습니다.

### 2) Cloudflare Tunnel 대상 변경

Zero Trust → **Networks** → **Tunnels** → 해당 터널 → **Public Hostname**

| 항목 | 값 |
|------|-----|
| Hostname | `sgb.mansejin.com` |
| Service | `http://sgb-gateway:8787` |

기존 `http://sgb-api:8787` 이면 **반드시** `sgb-gateway`로 바꿔야 터널이 게이트웨이를 거칩니다.

### 3) 수동 점검 모드 (선택)

```bash
# 점검 페이지 켜기
touch /volume1/docker/saenggibu/data/saenggibu/maintenance.on

# 점검 페이지 끄기
rm /volume1/docker/saenggibu/data/saenggibu/maintenance.on
```

## Cloudflare 502가 그대로일 때

게이트웨이·터널 컨테이너까지 모두 내려간 경우(첫 배포, 터널 재시작 등)에는 Cloudflare가 여전히 502를 보여 줄 수 있습니다.

**백업:** Cloudflare 대시보드 → **Error Pages** → **502** → Custom page  
→ `web/maintenance.html` 내용을 붙여 넣으면, 오리진이 완전히 죽어도 같은 문구를 보여 줄 수 있습니다.

## 로컬 개발

`python -m uvicorn` 등으로 API만 직접 띄울 때는 게이트웨이가 없습니다. 점검 페이지는 Docker 배포 경로에서만 적용됩니다.
