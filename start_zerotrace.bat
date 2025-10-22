@echo off
REM ZeroTrace Startup Script for Windows
REM This script starts i2pd and ZeroTrace client

echo.
echo ================================================================
echo            ZeroTrace P2P Messenger - Startup
echo ================================================================
echo.

REM Check if i2pd.exe exists
if not exist "i2pd.exe" (
    echo ERROR: i2pd.exe not found in current directory
    echo Please download i2pd from: https://i2pd.website/
    pause
    exit /b 1
)

REM Check if tunnels.conf exists
if not exist "tunnels.conf" (
    echo ERROR: tunnels.conf not found in current directory
    pause
    exit /b 1
)

echo Starting ZeroTrace with I2P integration...
echo.
echo I2P will be started automatically
echo Please wait for I2P destination to be displayed
echo.

REM Start ZeroTrace (which will start i2pd internally)
poetry run python -m src.zerotrace.main %*

echo.
echo ZeroTrace stopped.
pause
