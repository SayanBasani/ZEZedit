@echo off
setlocal enabledelayedexpansion

title ZEZEdit 2.0 - Local-First AI Video Editor

set "ZEZEDIT_ROOT=%~dp0"
if "%ZEZEDIT_ROOT:~-1%"=="\" set "ZEZEDIT_ROOT=%ZEZEDIT_ROOT:~0,-1%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ZEZEDIT_ROOT%\Start-ZEZEdit.ps1" %*
exit /b %errorlevel%
