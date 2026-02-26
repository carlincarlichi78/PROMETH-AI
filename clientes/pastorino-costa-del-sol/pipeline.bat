@echo off
REM SFCE Pipeline - Pastorino Costa del Sol
cd /d "%~dp0..\.."
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L
python scripts/pipeline.py --cliente pastorino-costa-del-sol --ejercicio 2025
pause
