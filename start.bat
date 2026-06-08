@echo off
title EDIAI Platform — Startup
color 0A

echo.
echo  ========================================
echo   EDIAI - AI Integration Engineer Platform
echo   Startup Script
echo  ========================================
echo.

:: ── Step 1: Check Ollama ──
echo [1/4] Checking Ollama...
where ollama >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   WARNING: Ollama not found in PATH
    echo   Download from: https://ollama.com/download
    echo   The backend will fall back to Groq Cloud.
    echo.
) else (
    echo   OK: Ollama found
    :: Check if deepseek-r1:8b model is available
    ollama list 2>nul | findstr /I "deepseek-r1:8b" >nul
    if %ERRORLEVEL% neq 0 (
        echo   WARNING: Model 'deepseek-r1:8b' not found
        echo   Run: ollama pull deepseek-r1:8b
        echo.
    ) else (
        echo   OK: Model deepseek-r1:8b available
    )
)
echo.

:: ── Step 2: Start Ollama (if available) ──
echo [2/4] Starting Ollama server...
where ollama >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "Ollama Server" ollama serve
    echo   OK: Ollama server starting in background
    timeout /t 3 /nobreak >nul
) else (
    echo   SKIP: Ollama not available
)
echo.

:: ── Step 3: Start Backend ──
echo [3/4] Starting FastAPI Backend (port 8000)...
cd /d "%~dp0backend"
if not exist "venv\Scripts\activate.bat" (
    echo   Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo   Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)
start "EDIAI Backend" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo   OK: Backend starting on http://localhost:8000
cd /d "%~dp0"
echo.

:: ── Step 4: Start Frontend ──
echo [4/4] Starting Next.js Frontend (port 3000)...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo   Installing npm dependencies...
    npm install
)
start "EDIAI Frontend" cmd /k "npm run dev"
echo   OK: Frontend starting on http://localhost:3000
cd /d "%~dp0"
echo.

echo  ========================================
echo   All services starting!
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   Health:    http://localhost:8000/api/health
echo.
echo   Generator: http://localhost:3000/generate
echo   Chat:      http://localhost:3000/chat
echo  ========================================
echo.
echo  Press any key to close this window...
pause >nul
