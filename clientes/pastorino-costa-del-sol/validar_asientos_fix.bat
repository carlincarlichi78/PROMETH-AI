@echo off
chcp 65001 >nul
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L

echo ========================================
echo  Validacion + CORRECCION de asientos 2025
echo  Pastorino Costa del Sol S.L.
echo ========================================
echo.
echo ATENCION: Este script CORRIGE errores de DIVISA y NC automaticamente.
echo.

python "%~dp0..\..\scripts\validar_asientos.py" --empresa 1 --ejercicio 2025 --fix

echo.
pause
