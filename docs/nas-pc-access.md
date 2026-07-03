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

#### 시놀로지: 먼저 사용자 홈 켜기 (필수)

키 등록 전에 **한 번만** DSM에서:

1. **제어판** → **사용자 및 그룹** → **고급** 탭
2. **사용자 홈 서비스 활성화** 체크 → 공유 폴더 `homes` 볼륨 선택 → **적용**
3. **ohola** 계정으로 DSM **한 번 로그인** (홈 폴더 생성)

이후 `/var/services/homes/ohola` 가 생겨야 키를 넣을 수 있습니다.

#### PC에서 키 등록

**한 번만 (비밀번호 마지막 1회 입력):**

```powershell
.\scripts\nas-pc.ps1 install-key -Profile local
```

또는 **`scripts\nas-install-key.bat`** 더블클릭

수동 (PowerShell — **경로를 그대로** 써야 함, `$HOME_DIR` 쓰면 Windows가 깨뜨림):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh saenggibu-nas-local "mkdir -p /var/services/homes/ohola/.ssh && cat >> /var/services/homes/ohola/.ssh/authorized_keys && chmod 700 /var/services/homes/ohola/.ssh && chmod 600 /var/services/homes/ohola/.ssh/authorized_keys"
```

또는 **`scripts\nas-copy-key.bat`** 더블클릭

`config/nas-pc.local.env`:

```env
NAS_SSH_KEY=C:\Users\Ohola\.ssh\id_ed25519
```

`.\scripts\nas-pc.ps1 setup` 으로 SSH config 갱신.

---

## 2. SMB — PC 탐색기에 `docker` 폴더 붙이기

나스 **안쪽**에는 `/volume1/docker` 가 있어도, **SMB 공유 폴더로 등록 안 하면**  
탐색기 `\\169.254.158.191` 에는 `homes`, `video`만 보이고 **`docker`는 안 보입니다.** (지금 상태)

### DSM에서 `docker` 공유 폴더 만들기 (한 번만)

1. DSM **제어판** → **공유 폴더** → **생성**
2. **이름:** `docker` (탐색기에 보일 이름)
3. **위치:** `volume1` (Container Manager 쓰는 볼륨)
4. 마법사 끝까지 → **ohola** 계정 **읽기/쓰기** 권한
5. **제어판** → **파일 서비스** → **SMB** 켜져 있는지 확인
6. PC 탐색기에서 `\\169.254.158.191` **새로고침** (F5)

성공하면 `homes`, `video` 옆에 **`docker`** 폴더가 생깁니다.  
안에 `saenggibu` 가 있으면 `\\169.254.158.191\docker\saenggibu` 로 접근.

#### 「이미 docker 폴더가 있다」고 나올 때

- **그대로 진행**하거나, 이름을 `docker2` 로 만들고 PC 설정만 바꿈:
  ```env
  NAS_SMB_SHARE=docker2
  ```
- File Station에서 실제 경로가 `/volume1/docker` 인지 확인

#### 공유 폴더 생성이 막힐 때 (SSH)

```bash
sudo synoshare --add docker /volume1/docker "" ohola administrators 0 0 0
```

(안 되면 DSM 관리자 계정으로 **제어판 → 공유 폴더**에서 수동 생성이 더 안전)

### PC에서 드라이브 연결 (Z:는 이미 쓰 중이면 Y:)

`config\nas-pc.local.env`:

```env
NAS_DRIVE_LETTER=Y
NAS_SMB_SHARE=docker
NAS_SMB_HOST_LOCAL=169.254.158.191
```

```powershell
.\scripts\nas-pc.ps1 map -Profile local
```

또는 한 줄:

```powershell
net use Y: \\169.254.158.191\docker /persistent:yes
```

탐색기: **`Y:\saenggibu`**

해제: `net use Y: /delete`

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
| `docker: command not found` (SSH update) | `update` copies latest `scripts/nas-docker-update.sh` via SMB (T:\saenggibu) first. Ensure `map -Profile local` works. Script uses Synology Container Manager paths + native `git pull`. |

---

## 관련 파일

- `config/nas-pc.example.env` — 설정 예시
- `config/nas-pc.local.env` — 본인 설정 (git 제외)
- `scripts/nas-pc.ps1` — SSH/SMB 명령
- `scripts/nas-docker-update.sh` — 나스 안에서 pull + rebuild
