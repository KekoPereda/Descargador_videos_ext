@echo off
rem Doble clic en el Explorador para arrancar el servidor local a mano.
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 servidor.py %*) else (python servidor.py %*)
pause
