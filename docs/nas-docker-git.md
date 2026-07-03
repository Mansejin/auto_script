# 나스 Docker로 git pull (Entware 불필요)

호스트에 `git` 없이 **Docker 이미지 `alpine/git`** 만으로 업데이트합니다.

경로: `/volume1/docker/saenggibu`

---

## 매번 업데이트 (이미 git clone 된 경우)

SSH 접속 후:

```bash
cd /volume1/docker/saenggibu
docker run --rm -v /volume1/docker/saenggibu:/git -w /git alpine/git pull origin cursor/saenggibu-writer-5821
```

또는 저장소 스크립트:

```bash
cd /volume1/docker/saenggibu
sh scripts/nas-docker-update.sh
```

그다음 **Container Manager** → `saenggibu` → **재시작** (Dockerfile 변경 시 **다시 빌드**)

---

## 처음 한 번 — ZIP으로만 넣어 둔 경우

`.git` 폴더가 없으면 `pull`이 안 됩니다. **한 번만** clone:

```bash
cd /volume1/docker
mv saenggibu saenggibu_backup

docker run --rm -v /volume1/docker:/git -w /git alpine/git \
  clone -b cursor/saenggibu-writer-5821 https://github.com/Mansejin/auto_script.git saenggibu

cp saenggibu_backup/.env saenggibu/.env
cp -a saenggibu_backup/data/saenggibu/. saenggibu/data/saenggibu/
```

확인:

```bash
ls /volume1/docker/saenggibu/.git
```

이후부터는 **매번 업데이트** 명령만 쓰면 됩니다.

---

## .git 있는지 확인

```bash
ls -la /volume1/docker/saenggibu/.git
```

- 있으면 → `docker run ... pull`
- 없으면 → 위 **처음 한 번** 절차

---

## Entware는?

설치 **안 해도 됩니다.** `entware.net | sh` 는 지금 HTML만 받아와서 실패하는 게 정상입니다. 더 시도하지 마세요.
