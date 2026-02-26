@echo off
chcp 65001 >nul
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L

echo ========================================
echo  Generando Excel libros contables 2025
echo  Pastorino Costa del Sol S.L.
echo ========================================
echo.

python "%~dp0..\..\scripts\crear_libros_contables.py" "%~dp02025\libros_contables_2025.xlsx" --empresa 1

echo.
pause
