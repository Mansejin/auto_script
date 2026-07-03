# PC에서 나스 SSH·SMB 쉽게 쓰기

SSH 매번 주소·비밀번호 치는 것과, 나스 파일을 PC 탐색기에서 못 보는 문제를 줄이기 위한 가이드입니다.

---

## 1. SSH — 원클릭 접속 (Windows)

### 최초 1회

1. 저장소 폴더에서 PowerShell 열기
2. 실행:

```powershell
.\scripts\nas-pc.ps1 setup
```

3. 열리는 `config/nas-pc.local.env` 에서 수정:
   - `NAS_USER` — 시놀로지 로그인 아이디
   - `NAS_SSH_HOST` — **Tailscale IP** (`100.x.x.x`, 밖에서 쓸 때)
   - `NAS_SSH_HOST_LOCAL` — **집 로컬 IP** (기본 `169.254.158.191`)

4. 저장 후 터미널에서 Enter

### 이후

| 방법 | 설명 |
|------|------|
| **`scripts\NAS-접속-로컬.bat`** | 집 안 — `169.254.158.191` SSH |
| **`scripts\NAS-업데이트-로컬.bat`** | 집 안 — pull + docker 재빌드 |
| **`scripts\NAS-드라이브-로컬.bat`** | 집 안 — `\\169.254.158.191\docker` → Z: |
| **`scripts\NAS-접속.bat`** | 밖 — Tailscale SSH |
| **`scripts\NAS-업데이트.bat`** | 밖 — Tailscale로 원격 업데이트 |
| `ssh saenggibu-nas-local` | 로컬 별칭 |
| `ssh saenggibu-nas` | Tailscale 별칭 |

### DSM에서 SSH 켜기

**제어판** → **터미널 및 SNMP** → **터미널** → **SSH 서비스 활성화**

### (선택) 비밀번호 없이 접속 — SSH 키

**한 번만 (비밀번호 마지막 1회 입력):**

```powershell
.\scripts\nas-pc.ps1 install-key -Profile local
```

또는 **`scripts\nas-install-key.bat`** 더블클릭

끝나면 `ssh saenggibu-nas-local` / `ssh saenggibu-nas` 비밀번호 없이 접속됩니다.

수동으로 하려면:

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\id_ed25519 -N '""'
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh saenggibu-nas-local "umask 077; mkdir -p .ssh; cat >> .ssh/authorized_keys; chmod 600 .ssh/authorized_keys"
```

`config/nas-pc.local.env` 에 추가 후 `.\scripts\nas-pc.ps1 setup`:

```env
NAS_SSH_KEY=C:\Users\Ohola\.ssh\id_ed25519
```

---

## 2. SMB — PC 탐색기에 `docker` 폴더 붙이기

나스의 `/volume1/docker` 는 **공유 폴더로 등록되어야** Windows에서 `\\나스\docker` 로 보입니다.

### DSM 설정 (한 번만)

#### 이미 `docker` 폴더가 있고 File Station에 보일 때

1. **제어판** → **공유 폴더**
2. 목록에 **`docker`** 가 있으면 → 선택 → **편집** → **권한** 탭에서 본인 계정 **읽기/쓰기**
3. **제어판** → **파일 서비스** → **SMB** → **SMB 서비스 활성화** 확인

#### `docker` 가 공유 폴더 목록에 없을 때

**경로에 데이터가 거의 없을 때 (새로 만들어도 됨)**

1. **제어판** → **공유 폴더** → **생성**
2. 이름: `docker`
3. 위치: `volume1`
4. 본인 계정 읽기/쓰기
5. `saenggibu` 등 기존 내용이 다른 곳에 있으면 File Station에서 `docker` 안으로 옮기기

**이미 `/volume1/docker/saenggibu` 에 서비스가 돌고 있을 때**

- 공유 폴더 이름을 `docker` 로 만들면 보통 **같은 경로**(`/volume1/docker`)를 가리킵니다.
- 이름 충돌이 나면 공유 폴더 이름을 `docker-dev` 로 만들고, PC에서는 `NAS_SMB_SHARE=docker-dev` 로 맞추면 됩니다.

### PC에서 드라이브 연결

```powershell
.\scripts\nas-pc.ps1 map
```

기본: `Z:` → `\\ohola.synology.me\docker`

탐색기에서 **`Z:\saenggibu`** 로 `.env`, `data`, `web/admin` 파일을 메모장·VS Code로 바로 열 수 있습니다.

해제:

```powershell
.\scripts\nas-pc.ps1 unmap
```

### 집 밖(스튜디오)에서 SMB

- **Tailscale** 설치된 PC + 나스면 `NAS_SMB_HOST=100.x.x.x` (나스 Tailscale IP)
- QuickConnect만으로는 SMB가 느리거나 막힐 수 있음 → Tailscale 권장

---

## 3. SSH 없이 파일만 다루고 싶을 때

| 할 일 | 방법 |
|--------|------|
| `.env` 수정 | `Z:\saenggibu\.env` 메모장으로 편집 |
| UI 파일 수정 | `Z:\saenggibu\web\admin\` (볼륨 마운트라 저장 즉시 반영) |
| 코드 업데이트 | `NAS-업데이트.bat` 더블클릭 또는 나스 **작업 스케줄러** 자동 pull |
| 컨테이너 재시작 | DSM **Container Manager** 에서 재시작 |

---

## 4. 문제 해결

| 증상 | 확인 |
|------|------|
| SSH 연결 거부 | DSM SSH 활성화, 방화벽 22번, Tailscale 같은 네트워크 |
| SMB 로그인 창만 뜸 | 시놀로지 계정·비밀번호, 공유 폴더 권한 |
| `Z:` 안 보임 | `.\scripts\nas-pc.ps1 status` → `map` 재실행 |
| 밖에서 SMB 안 됨 | `NAS_SMB_HOST` 를 Tailscale IP로 변경 |

---

## 관련 파일

- `config/nas-pc.example.env` — 설정 예시
- `config/nas-pc.local.env` — 본인 설정 (git 제외)
- `scripts/nas-pc.ps1` — SSH/SMB 명령
- `scripts/nas-docker-update.sh` — 나스 안에서 pull + rebuild
