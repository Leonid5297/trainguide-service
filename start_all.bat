@echo off
REM ============================================================
REM  TrainGuide — запуск всех сервисов одной командой
REM  Запускать из папки: trainguide\
REM ============================================================

set VENV=venv\trainguide\Scripts\activate.bat

echo.
echo =====================================================
echo   TrainGuide — запуск всех сервисов
echo =====================================================
echo.

REM --- Django монолит (порт 8000) ---
echo [1/7] Django монолит          → http://localhost:8000
start "Django :8000" cmd /k "call %VENV% && cd trainguide && python manage.py runserver 8000"
timeout /t 2 /nobreak >nul

REM --- workout-service (порт 8001) ---
echo [2/7] workout-service         → http://localhost:8001/docs
start "workout :8001" cmd /k "call %VENV% && cd workout-service && uvicorn main:app --reload --port 8001"
timeout /t 1 /nobreak >nul

REM --- analytics-service (порт 8002) ---
echo [3/7] analytics-service       → http://localhost:8002/docs
start "analytics :8002" cmd /k "call %VENV% && cd analytics-service && uvicorn main:app --reload --port 8002"
timeout /t 1 /nobreak >nul

REM --- notification-service (порт 8003) ---
echo [4/7] notification-service    → http://localhost:8003/docs
start "notification :8003" cmd /k "call %VENV% && cd notification-service && uvicorn main:app --reload --port 8003"
timeout /t 1 /nobreak >nul

REM --- export-service (порт 8004) ---
echo [5/7] export-service          → http://localhost:8004/docs
start "export :8004" cmd /k "call %VENV% && cd export-service && uvicorn main:app --reload --port 8004"
timeout /t 1 /nobreak >nul

REM --- advisor-service (порт 8005) ---
echo [6/7] advisor-service         → http://localhost:8005/docs
start "advisor :8005" cmd /k "call %VENV% && cd advisor-service && uvicorn main:app --reload --port 8005"
timeout /t 1 /nobreak >nul

REM --- schedule-service (порт 8006) ---
echo [7/7] schedule-service        → http://localhost:8006/docs
start "schedule :8006" cmd /k "call %VENV% && cd schedule-service && uvicorn main:app --reload --port 8006"

echo.
echo =====================================================
echo   Все сервисы запущены! Открылось 7 окон.
echo.
echo   Django      → http://localhost:8000
echo   Workout     → http://localhost:8001/docs
echo   Analytics   → http://localhost:8002/docs
echo   Notif       → http://localhost:8003/docs
echo   Export      → http://localhost:8004/docs
echo   Advisor     → http://localhost:8005/docs
echo   Schedule    → http://localhost:8006/docs
echo =====================================================
echo.
pause
