@echo off
REM SFCE Pipeline - Pastorino Prueba (testing)
cd /d "%~dp0..\.."
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L
python scripts/pipeline.py --cliente pastorino-prueba --ejercicio 2025
pause
