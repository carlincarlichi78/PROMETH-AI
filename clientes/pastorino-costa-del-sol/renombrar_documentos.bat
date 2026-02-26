@echo off
set FS_API_TOKEN=iOXmrA1Bbn8RDWXLv91L
echo === Renombramiento de documentos (DRY-RUN) ===
echo.
echo Ejecutando en modo preview (sin cambios)...
echo Para ejecutar de verdad, quitar --dry-run
echo.
python ..\..\scripts\renombrar_documentos.py --cliente pastorino-costa-del-sol --empresa 1 --cif B13995519 --dry-run
echo.
pause
