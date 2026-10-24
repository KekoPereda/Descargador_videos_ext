@echo off
rem Doble clic en el Explorador para instalar en Windows. Volver a ejecutarlo si mueves la carpeta.
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 instalar_windows.py
) else (
  python --version >nul 2>nul
  if errorlevel 1 (
    echo No se encontro Python.
    echo Instalalo desde https://www.python.org/downloads/ marcando "Add python.exe to PATH",
    echo o abre PowerShell y ejecuta:  winget install Python.Python.3.12
    echo Despues vuelve a ejecutar este archivo.
  ) else (
    python instalar_windows.py
  )
)
pause
