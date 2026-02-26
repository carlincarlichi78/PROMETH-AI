@echo off
chcp 65001 >nul
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L

echo ========================================
echo  Resumen fiscal 2025
echo  Pastorino Costa del Sol S.L.
echo ========================================
echo.

python "%~dp0..\..\scripts\resumen_fiscal.py" --empresa 1 --ejercicio 2025

echo.
pause
