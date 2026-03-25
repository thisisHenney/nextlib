@echo off

:: Save current directory
set "CUR_DIR=%cd%"

:: Move to batch file directory
cd /d "%~dp0"

:: Check if first argument is an option (starts with -)
set FIRST=%~1
if "%FIRST:~0,1%"=="-" (
    python convert_ui.py "%CUR_DIR%" %*
) else if "%~1"=="" (
    python convert_ui.py "%CUR_DIR%"
) else (
    python convert_ui.py "%CUR_DIR%" %*
)

:: Restore original directory
cd /d "%CUR_DIR%"
