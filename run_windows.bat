@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Chua co moi truong ao. Hay chay setup_windows.bat truoc.
    pause
    exit /b 1
)
echo Dang chay HPO va toi uu da muc tieu...
.venv\Scripts\python.exe run_project.py
if errorlevel 1 (
    echo Co loi khi chay. Hay xem thong bao phia tren.
) else (
    echo Hoan tat. Kiem tra thu muc results va figures.
)
pause
