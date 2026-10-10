@echo off
rem On another PC: only the Venus Node, connected to Core on your main PC.
rem See setup-venus.ps1 (-NodeOnly) and README "Another PC".
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-venus.ps1" -NodeOnly
pause
