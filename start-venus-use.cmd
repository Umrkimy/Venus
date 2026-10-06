@echo off
rem Double-click for everyday use: lighter on RAM, no auto-reload. See start-venus.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-venus.ps1" -Use
if errorlevel 1 pause
