@echo off
REM Test I2P Manager functionality

echo.
echo ================================================================
echo         Testing I2P Manager for ZeroTrace
echo ================================================================
echo.

poetry run python -c "from src.zerotrace.i2p_manager import test_i2p_manager; test_i2p_manager()"

pause
