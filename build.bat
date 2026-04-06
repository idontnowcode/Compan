@echo off
REM Rested - PyInstaller 빌드 스크립트
REM 실행 전: pip install -r requirements.txt pyinstaller

echo [1/3] 의존성 확인...
pip install -r requirements.txt pyinstaller

echo [2/3] PyInstaller로 .exe 빌드 중...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name Rested ^
    --icon assets\icon.png ^
    --add-data "assets;assets" ^
    --paths src ^
    src\main.py

echo [3/3] 완료!
echo 실행 파일 위치: dist\Rested.exe
pause
