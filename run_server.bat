@echo off
REM Run the C2 Server with proper PYTHONPATH

echo [*] Starting C2 Server...
echo [*] Setting PYTHONPATH to project root...
echo.

REM Set PYTHONPATH to current directory (project root)
set PYTHONPATH=%~dp0

REM Run the server
py server\server.py
