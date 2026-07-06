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

**중요:** DSM 작업은 repo 안의 `nas-docker-update.sh` 를 **직접 실행하지 마세요** (SMB로 더러워진 옛 파일). 아래 `nas-dsm-task.sh` 를 사용합니다.

1. 나스에 파일 복사 (PC `git pull` 후 탐색기 `K:\saenggibu\scripts\nas-dsm-task.sh` 복사되게 deploy 1회 성공 후, 또는 SSH):

```bash
curl -fsSL https://raw.githubusercontent.com/Mansejin/auto_script/main/scripts/nas-dsm-task.sh \
  -o /volume1/docker/saenggibu/scripts/nas-dsm-task.sh
chmod +x /volume1/docker/saenggibu/scripts/nas-dsm-task.sh
```

2. **더러운 git 한 번 정리** (merge 오류 났을 때만):

```bash
curl -fsSL https://raw.githubusercontent.com/Mansejin/auto_script/main/scripts/nas-one-time-git-reset.sh | sh
```

3. DSM → **작업 스케줄러** → `saenggibu-auto-pull` → 사용자 **`root`**
4. **작업 설정** 스크립트:

```bash
sh /volume1/docker/saenggibu/scripts/nas-dsm-task.sh
```

5. 나스 `.env` (선택):

```env
SGB_DEPLOY_BRANCH=main
SGB_DOCKER_SUDO=1
```

### 이후

```
코드 수정 → git push → (최대 10분) → sgb.mansejin.com 반영
```

로그: `/volume1/docker/saenggibu/logs/scheduled-pull.log`  
(없으면 스크립트가 아직 한 번도 안 돌았거나, DSM 스크립트를 `sh /volume1/docker/saenggibu/scripts/nas-scheduled-pull.sh` 로 실행했는지 확인)  
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
| `cannot access docker daemon` | **A)** PC `config/nas-pc.local.env`에 `NAS_SUDO_PASSWORD=ohola비밀번호` 추가 후 deploy 재실행. **B)** 나스에서 root로 1회: `sh scripts/nas-setup-docker-sudo.sh` (DSM 작업 스케줄러). **C)** 스케줄러 사용자 **root** |
| `git: command not found` (NAS SSH) | 정상. 나스에 Git 패키지 없음. deploy는 **docker로 git sync** (최신 스크립트 필요). `git pull` 수동 명령은 안 됨 |
| 10분 지나도 안 바뀜 | `scheduled-pull.log`, `deploy.log` 확인 |

---

## 관련 파일

- `scripts/nas-scheduled-pull.sh` — DSM 스케줄러용
- `scripts/nas-docker-update.sh` — pull + docker rebuild
- `.github/workflows/deploy-nas.yml` — Actions (Tailscale + SSH)
