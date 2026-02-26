@echo off
chcp 65001 >nul
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L

echo ========================================
echo  Validacion de asientos 2025
echo  Pastorino Costa del Sol S.L.
echo ========================================
echo.

python "%~dp0..\..\scripts\validar_asientos.py" --empresa 1 --ejercicio 2025

echo.
echo Para corregir automaticamente errores de DIVISA y NC, ejecuta:
echo   validar_asientos_fix.bat
echo.
pause
