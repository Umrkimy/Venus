@echo off
rem Double-click to start Venus. See start-venus.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-venus.ps1"
if errorlevel 1 pause
