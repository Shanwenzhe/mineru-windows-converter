@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0"
if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" "%~dp0MinerU转换器.pyw" %*
) else (
    py -3 "%~dp0MinerU转换器.pyw" %*
)
set "converter_exit=%ERRORLEVEL%"
if not "%converter_exit%"=="0" (
    echo.
    echo Startup failed. Check the error above and the README installation steps.
    pause
)
popd
exit /b %converter_exit%
