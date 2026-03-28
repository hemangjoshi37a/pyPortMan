@echo off
REM Quick start script for pyPortMan React Dashboard

echo Starting pyPortMan React Dashboard...
echo ====================================
echo.

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        echo Please ensure Node.js and npm are installed
        pause
        exit /b 1
    )
    echo.
)

REM Start the development server
echo Starting development server on http://localhost:3000
echo Press Ctrl+C to stop
echo.
call npm run dev

if errorlevel 1 (
    echo Error: Failed to start server
    pause
)
