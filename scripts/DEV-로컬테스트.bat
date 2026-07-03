@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title 생기부 로컬 테스트 서버
echo.
echo [폴더] %CD%
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev-local.ps1" %*
if errorlevel 1 (
  echo.
  echo ========================================
  echo  서버 시작 실패
  echo ========================================
  echo  - Python 설치 및 PATH 확인
  echo  - 이 폴더에 .env 있는지 확인
  echo  - 포트 8787 사용 중이면 다른 프로그램 종료
  echo.
  pause
)
