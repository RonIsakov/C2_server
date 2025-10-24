@echo off
REM Run the C2 Client with proper PYTHONPATH

echo [*] Starting C2 Client...
echo [*] Setting PYTHONPATH to project root...
echo.

REM Set PYTHONPATH to current directory (project root)
set PYTHONPATH=%~dp0

REM Run the client
py client\client.py
