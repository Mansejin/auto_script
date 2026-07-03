# NAS 자동 배포 (push만 하면 됨)

수동으로 나스 SSH · `git pull` · docker 재시작을 반복하지 않아도 되도록 **두 가지 자동화**를 씁니다.

| 방식 | 속도 | 설정 |
|------|------|------|
| **GitHub Actions** (권장) | push 후 1~3분 | GitHub Secrets 1회 |
| **나스 작업 스케줄러** (백업) | 5~15분마다 | DSM 작업 1회 |

둘 다 켜 두면 Actions가 실패해도 스케줄러가 따라잡습니다.

---

## 1. GitHub Actions (push → 자동 배포)

### 1-1. 나스 SSH 키 (이미 `nas-pc.ps1 install-key` 했다면 생략 가능)

PC PowerShell:

```powershell
cd C:\Users\Ohola\Documents\GitHub\auto_script
.\scripts\nas-pc.ps1 install-key -Profile remote
```

Tailscale IP(`100.x.x.x`)로 키 로그인이 되어야 GitHub에서도 접속됩니다.

### 1-2. GitHub Secrets 등록

저장소 **Mansejin/auto_script** → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | 값 예시 |
|--------|---------|
| `NAS_SSH_HOST` | `100.72.192.38` (Tailscale) 또는 DDNS |
| `NAS_SSH_USER` | `ohola` |
| `NAS_SSH_KEY` | `C:\Users\Ohola\.ssh\id_ed25519` **파일 전체** (BEGIN~END 포함) |
| `NAS_SSH_PORT` | (선택) `22` |
| `NAS_REPO_PATH` | (선택) `/volume1/docker/saenggibu` |

> **중요:** Actions 러너는 집 밖에서 돌아가므로 **로컬 LAN IP(`169.254.x.x`)는 쓰지 마세요.** Tailscale·DDNS·공인 IP 중 나스에 SSH 되는 주소를 넣습니다.

### 1-3. 나스 `.env`에 배포 브랜치 (선택)

`/volume1/docker/saenggibu/.env`:

```env
SGB_DEPLOY_BRANCH=main
```

비우면 워크플로가 **push한 브랜치**를 그대로 배포합니다 (`main`, `cursor/saenggibu-writer-5821` 등).

### 1-4. 동작 확인

1. `main`(또는 배포 브랜치)에 push
2. GitHub → **Actions** → **Deploy to NAS** 실행 로그 확인
3. `https://sgb.mansejin.com/health` → `{"status":"ok"}`

수동 실행: Actions → **Deploy to NAS** → **Run workflow**

---

## 2. 나스 작업 스케줄러 (백업, GitHub 없이도 pull)

GitHub Secrets를 아직 안 넣었거나, Actions가 막혔을 때를 대비합니다.

1. DSM → **제어판** → **작업 스케줄러** → **생성** → **예약된 작업** → **사용자 정의 스크립트**
2. **일반**: 이름 `saenggibu-auto-pull`, 사용자 `root`
3. **일정**: 매 **10분** (또는 매일 새벽 3시)
4. **작업 설정** → 스크립트:

```bash
/volume1/docker/saenggibu/scripts/nas-scheduled-pull.sh
```

로그: `/volume1/docker/saenggibu/logs/scheduled-pull.log`

---

## 3. PC에서 할 일 (이제 선택)

자동 배포가 켜지면 **매번 나스 pull 할 필요 없습니다.**

| 상황 | PC 명령 |
|------|---------|
| 급히 지금 반영 | `.\scripts\nas-pc.ps1 update -Profile local` |
| UI만 빠르게 (SMB) | `.\scripts\nas-pc.ps1 sync-ui -Profile local` |
| 로컬에서 push | `git push` → Actions가 나스 배포 |

---

## 4. 관리자 페이지(UI) 반영

- `web/admin` 은 docker **볼륨 마운트** → `git pull` 만으로도 파일은 갱신됩니다.
- 브라우저 **Ctrl+F5** (캐시 무시).
- `index.html` 의 `?v=` 쿼리가 바뀌면 새 JS가 로드됩니다.

---

## 5. 문제 해결

| 증상 | 확인 |
|------|------|
| Actions가 Skip | `NAS_SSH_*` Secrets 미설정 → 1-2절 |
| SSH connection refused | 나스 DSM SSH 켜짐, Tailscale 같은 네트워크 |
| `docker: permission denied` | 나스 `.env`에 `SGB_DOCKER_SUDO=1` 추가. GitHub Actions는 자동으로 sudo 시도함. DSM에서 사용자를 `administrators` 그룹에 넣거나 passwordless sudo 설정 |
| 잘못된 브랜치 배포 | `.env`의 `SGB_DEPLOY_BRANCH` 또는 push 브랜치 확인 |
| UI만 옛날 | Ctrl+F5, 또는 `sync-ui` |

배포 로그 (나스): `/volume1/docker/saenggibu/logs/deploy.log`
