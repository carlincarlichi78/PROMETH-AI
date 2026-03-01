@echo off
cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD

REM Cargar variables de entorno desde .env
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A:~0,1%"=="#" if not "%%A"=="" set "%%A=%%B"
)

REM Arrancar API backend (puerto 8000)
start "SFCE API" cmd /k "cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD && uvicorn sfce.api.app:crear_app --factory --reload --port 8000"

REM Esperar a que la API arranque
timeout /t 4 /nobreak > nul

REM Arrancar Dashboard frontend (puerto 3000)
start "SFCE Dashboard" cmd /k "cd /d C:\Users\carli\PROYECTOS\CONTABILIDAD\dashboard && npm run dev"

REM Esperar a que Vite compile
timeout /t 6 /nobreak > nul

REM Abrir navegador
start http://localhost:3000
