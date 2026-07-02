# mansejin.com 관리자 페이지 배포

`tools-site` 저장소에 아래 파일을 복사하면 **https://mansejin.com/admin/saenggibu/** 에서 관리자 UI가 열립니다.

```
admin/saenggibu/index.html
admin/saenggibu/css/admin.css
admin/saenggibu/js/admin.js
robots.txt  (또는 기존 파일에 Disallow: /admin/ 추가)
```

## 설정

1. **먼저** `auto_script`에서 `./scripts/build-deploy-admin.sh` 실행 (web/admin → deploy 복사 + 경로 변환)
2. `./scripts/sync-tools-site-admin.sh /path/to/tools-site` 로 tools-site에 복사
3. API 서버 `.env`의 `SGB_ALLOWED_ORIGINS`에 `https://mansejin.com` 포함
4. GitHub Pages 배포 후 URL 직접 접속 (공개 메뉴 없음)

`index.html` (build 스크립트가 자동 설정):

```html
<body data-api-base="https://sgb.mansejin.com" data-assets-base="">
<link rel="stylesheet" href="css/style.css">
<script src="js/admin.js"></script>
```

> **주의:** `web/admin/index.html`을 deploy에 직접 복사하면 CSS가 깨집니다 (`/admin-static/` 은 나스 전용).

상세 연동: `auto_script/docs/deploy-mansejin.md`

## 보안

- `robots.txt`: `/admin/` 차단
- HTML `noindex` 메타
- 실제 인증은 API 서버 `ADMIN_PASSWORD`

이 폴더의 `admin/` 내용을 `Mansejin/tools-site` 루트에 그대로 복사하세요.
