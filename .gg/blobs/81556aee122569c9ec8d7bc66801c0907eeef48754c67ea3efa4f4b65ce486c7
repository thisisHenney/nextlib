@echo off

:: 현재 경로 저장
set "CUR_DIR=%cd%"

:: 배치파일이 있는 폴더로 이동
cd /d "%~dp0"

:: 옵션만 입력했는지 확인 (첫 인자가 -로 시작하면 옵션만 입력한 것)
set FIRST=%~1
if "%FIRST:~0,1%"=="-" (
    python convert_ui.py "%CUR_DIR%" %*
) else if "%~1"=="" (
    python convert_ui.py "%CUR_DIR%"
) else (
    python convert_ui.py "%CUR_DIR%" %*
)

:: 원래 경로로 복귀
cd /d "%CUR_DIR%"
