# mansejin.com 관리자 페이지 배포

`tools-site` 저장소에 아래 파일을 복사하면 **https://mansejin.com/admin/saenggibu/** 에서 관리자 UI가 열립니다.

```
admin/saenggibu/index.html
admin/saenggibu/css/admin.css
admin/saenggibu/js/admin.js
robots.txt  (또는 기존 파일에 Disallow: /admin/ 추가)
```

## 설정

1. `admin/saenggibu/index.html`의 `data-api-base`에 `server.py`를 배포한 API 주소 입력
2. API 서버 `.env`의 `SGB_ALLOWED_ORIGINS`에 `https://mansejin.com` 포함
3. GitHub Pages 배포 후 URL 직접 접속 (공개 메뉴 없음)

## 보안

- `robots.txt`: `/admin/` 차단
- HTML `noindex` 메타
- 실제 인증은 API 서버 `ADMIN_PASSWORD`

이 폴더의 `admin/` 내용을 `Mansejin/tools-site` 루트에 그대로 복사하세요.
