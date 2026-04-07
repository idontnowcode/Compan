@echo off
REM Rested - 실행 스크립트 (더블클릭으로 바로 실행)

cd /d "%~dp0"

echo [1/2] 의존성 설치 중...
pip install -r requirements.txt >nul 2>&1

echo [2/2] Rested 시작...
python src\main.py %*
