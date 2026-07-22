@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.conda\python.exe"

if not exist "%PYTHON%" (
    set "PYTHON=python"
)

echo.
echo ==========================================
echo  Project4 - Create MySQL Database
echo ==========================================
echo.
echo Python: %PYTHON%
echo.

%PYTHON% "%ROOT%tools\dev\create_database.py" %*
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
    echo Database initialization failed. Exit code: %EXITCODE%
) else (
    echo Database initialization finished successfully.
)
echo.
pause
exit /b %EXITCODE%
