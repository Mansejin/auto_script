# NAS 자동 배포 (직접 pull 안 해도 됨)

GitHub에 push만 하면 나스가 알아서 최신 코드를 받습니다. **아래 둘 중 하나만** 설정하면 됩니다.

| 방식 | 속도 | 난이도 | 추천 |
|------|------|--------|------|
| **A. 나스 작업 스케줄러** | 최대 10분 | 쉬움 | 집에 Tailscale 설정 귀찮을 때 |
| **B. GitHub Actions + Tailscale** | 1~3분 | 보통 | 빠른 배포 원할 때 |

둘 다 켜도 됩니다.

---

## A. 나스 작업 스케줄러 (가장 확실, 추천)

GitHub 서버가 집 나스에 직접 못 들어와도 **나스가 밖으로 나가서** GitHub에서 pull 합니다.

### 한 번만 설정

1. DSM → **제어판** → **작업 스케줄러** → **생성** → **예약된 작업** → **사용자 정의 스크립트**
2. **일반**: 이름 `saenggibu-auto-pull`, 사용자 **`root`**
3. **일정**: **매 10분** (`0,10,20,30,40,50` 분 — DSM UI에 맞게 설정)
4. **작업 설정** → 스크립트:

```bash
/volume1/docker/saenggibu/scripts/nas-scheduled-pull.sh
```

> 스크립트가 없으면 PC에서 한 번만: `.\scripts\nas-pc.ps1 update -Profile local`

5. 나스 `.env` (선택):

```env
SGB_DEPLOY_BRANCH=cursor/saenggibu-writer-5821
SGB_DOCKER_SUDO=1
```

### 이후

```
코드 수정 → git push → (최대 10분) → sgb.mansejin.com 반영
```

로그: `/volume1/docker/saenggibu/logs/scheduled-pull.log`  
배포 로그: `/volume1/docker/saenggibu/logs/deploy.log`

---

## B. GitHub Actions + Tailscale (push 후 1~3분)

### 왜 Tailscale 키가 필요한가?

`dial tcp ...:22: i/o timeout` 은 **GitHub 클라우드가 집 나스에 닿지 못해서** 납니다.  
`169.254.x.x`(로컬)나 막힌 공인 IP로는 안 됩니다. Actions 러너를 **Tailscale 망에 잠깐 붙여** 나스 `100.x.x.x`로 SSH 합니다.

### B-1. Tailscale Auth Key 발급

1. https://login.tailscale.com/admin/settings/keys
2. **Generate auth key**
   - Ephemeral: **ON** (CI용)
   - Reusable: ON
3. 키 복사 (한 번만 보임)

### B-2. GitHub Secrets

저장소 **Settings → Secrets → Actions**:

| Secret | 값 |
|--------|-----|
| `TAILSCALE_AUTHKEY` | 위에서 복사한 키 |
| `NAS_SSH_HOST` | 나스 **Tailscale IP** (`100.72.192.38` 등) |
| `NAS_SSH_USER` | `ohola` |
| `NAS_SSH_KEY` | `id_ed25519` 파일 **전체** 내용 |
| `NAS_REPO_PATH` | (선택) `/volume1/docker/saenggibu` |

**쓰면 안 되는 주소:** `169.254.158.191` (집 안에서만 됨)

### B-3. 나스 쪽 확인

- DSM **SSH** 켜짐
- 나스에 **Tailscale** 설치·로그인·Online
- PC에서 `ssh ohola@100.x.x.x` 되면 Actions도 같은 IP 사용

### B-4. 테스트

Actions → **Deploy to NAS** → **Run workflow**

성공 로그: `NAS SSH port open` → `==> git pull` → `==> done`

---

## PC에서 할 일 (이제 거의 없음)

| 상황 | 명령 |
|------|------|
| 평소 | `git push` 만 |
| 급히 지금 | `.\scripts\nas-pc.ps1 deploy -Profile local` |
| UI만 | `.\scripts\NAS-UI-동기화.bat` 후 Ctrl+F5 |

---

## 문제 해결

| 증상 | 해결 |
|------|------|
| `i/o timeout` (port 22) | **A안 스케줄러** 쓰거나 **B안** `TAILSCALE_AUTHKEY` + Tailscale IP |
| Actions Skip | Secrets 4개 모두 등록 |
| `docker: permission denied` | 나스 `.env`에 `SGB_DOCKER_SUDO=1`, 스케줄러 사용자 `root` |
| UI만 옛날 | Ctrl+F5, `sync-ui` |
| 10분 지나도 안 바뀜 | `scheduled-pull.log`, `deploy.log` 확인 |

---

## 관련 파일

- `scripts/nas-scheduled-pull.sh` — DSM 스케줄러용
- `scripts/nas-docker-update.sh` — pull + docker rebuild
- `.github/workflows/deploy-nas.yml` — Actions (Tailscale + SSH)
