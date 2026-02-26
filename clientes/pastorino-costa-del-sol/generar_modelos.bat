@echo off
chcp 65001 >nul
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L

echo ========================================
echo  Generando modelos fiscales 2025
echo  Pastorino Costa del Sol S.L.
echo ========================================
echo.

python "%~dp0..\..\scripts\generar_modelos_fiscales.py" "%~dp0." --ejercicio 2025 --empresa 1

echo.
pause
