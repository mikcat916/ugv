@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.conda\python.exe"

if not exist "%PYTHON%" (
    set "PYTHON=py"
)

echo.
echo ==========================================
echo  Project4 - MySQL Diagnose
echo ==========================================
echo.

%PYTHON% "%ROOT%scripts\test_mysql_connection.py" %*
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
    echo Diagnose finished with errors. Check the log file under logs\.
) else (
    echo Diagnose finished successfully.
)
echo.
pause
exit /b %EXITCODE%
