@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo [1/3] Dang tao moi truong ao Python...
    py -3.11 -m venv .venv
    if errorlevel 1 goto error
)
echo [2/3] Dang cai dat thu vien...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo Cai dat hoan tat. Hay chay run_windows.bat de bat dau thi nghiem.
pause
exit /b 0
:error
echo.
echo Co loi trong qua trinh cai dat. Hay kiem tra Python 3.11 da duoc cai dat va lenh py co hoat dong.
pause
exit /b 1
