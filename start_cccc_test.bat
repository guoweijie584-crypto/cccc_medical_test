@echo off
setlocal
chcp 65001 >nul

set "PROJECT_ROOT=H:\project\cccc_test"
set "CCCC_HOME=%PROJECT_ROOT%\.cccc_home"
set "CCCC_NATIVE_HOME=%CCCC_HOME%"
set "CCCC_REPO_SRC=%PROJECT_ROOT%\cccc_medical-main\src"
set "CCCC_DAEMON_PORT=9766"
set "CCCC_WEB_HOST=127.0.0.1"
set "CCCC_WEB_PORT=8858"
set "WEB_DEV_PORT=5173"
set "MEMORY_PALACE_PORT=8000"
set "MEMORY_PALACE_HOST=127.0.0.1"

echo ==========================================
echo   CCCC Test Launcher (isolated)
echo ==========================================
echo.
echo CCCC_HOME        = %CCCC_HOME%
echo CCCC_NATIVE_HOME = %CCCC_NATIVE_HOME%
echo CCCC_REPO_SRC    = %CCCC_REPO_SRC%
echo CCCC_DAEMON_PORT = %CCCC_DAEMON_PORT%
echo CCCC_WEB_PORT    = %CCCC_WEB_PORT%
echo WEB_DEV_PORT     = %WEB_DEV_PORT%
echo MEMORY_PALACE    = http://%MEMORY_PALACE_HOST%:%MEMORY_PALACE_PORT%/
echo.

if not exist "%CCCC_HOME%" mkdir "%CCCC_HOME%"

echo [cleanup] Releasing test ports 5173 / 8000 / 8001 / 8858 / 9766...
call :kill_port 5173
call :kill_port 8000
call :kill_port 8001
call :kill_port 8858
call :kill_port 9766

echo [setup] Syncing isolated CCCC home...
call cmd /c "set CCCC_HOME=%CCCC_HOME%&& set CCCC_NATIVE_HOME=%CCCC_NATIVE_HOME%&& set CCCC_DAEMON_PORT=%CCCC_DAEMON_PORT%&& set PYTHONPATH=%CCCC_REPO_SRC%&& python -m cccc.cli.main attach \"%PROJECT_ROOT%\""
if errorlevel 1 (
    echo [error] Failed to initialize isolated CCCC home.
    pause
    exit /b 1
)

echo [1/6] Starting isolated CCCC daemon...
start "CCCC Test Daemon" cmd /k "cd /d %PROJECT_ROOT% && set CCCC_HOME=%CCCC_HOME% && set CCCC_DAEMON_PORT=%CCCC_DAEMON_PORT% && set PYTHONPATH=%CCCC_REPO_SRC% && python -m cccc.daemon_main run"

timeout /t 4 /nobreak >nul

echo [2/6] Bootstrapping CCCC-native medical groups...
call cmd /c "set CCCC_HOME=%CCCC_HOME%&& set CCCC_NATIVE_HOME=%CCCC_NATIVE_HOME%&& set CCCC_DAEMON_PORT=%CCCC_DAEMON_PORT%&& set PYTHONPATH=%CCCC_REPO_SRC%&& python bootstrap_cccc_native.py --runtime codex"
if errorlevel 1 (
    echo [error] Failed to bootstrap CCCC-native medical groups.
    pause
    exit /b 1
)

timeout /t 4 /nobreak >nul

echo [3/6] Starting Memory Palace on %MEMORY_PALACE_PORT%...
start "CCCC Test Memory Palace" cmd /k "cd /d %PROJECT_ROOT%\\Memory-Palace-main\\backend && set MCP_API_KEY=local-dev-key-12345 && python main.py"

timeout /t 4 /nobreak >nul

echo [4/6] Starting isolated CCCC web on %CCCC_WEB_PORT%...
start "CCCC Test CCCC Web" cmd /k "cd /d %PROJECT_ROOT% && set CCCC_HOME=%CCCC_HOME% && set CCCC_NATIVE_HOME=%CCCC_NATIVE_HOME% && set CCCC_DAEMON_PORT=%CCCC_DAEMON_PORT% && python scripts\run_cccc_web.py --host %CCCC_WEB_HOST% --port %CCCC_WEB_PORT%"

echo [wait] Waiting for CCCC web health on %CCCC_WEB_HOST%:%CCCC_WEB_PORT%...
call :wait_http_ready "http://%CCCC_WEB_HOST%:%CCCC_WEB_PORT%/api/v1/health" 45
if errorlevel 1 (
    echo [error] CCCC Web did not become healthy on %CCCC_WEB_HOST%:%CCCC_WEB_PORT%.
    if exist "%CCCC_HOME%\daemon\cccc-web.log" (
        echo [debug] Last lines from %CCCC_HOME%\daemon\cccc-web.log:
        powershell -NoProfile -Command "Get-Content -Path '%CCCC_HOME%\daemon\cccc-web.log' -Tail 80"
    )
    pause
    exit /b 1
)

echo [5/6] Starting medical API on 8001...
start "CCCC Test API" cmd /k "cd /d %PROJECT_ROOT% && set CCCC_HOME=%CCCC_HOME% && set CCCC_NATIVE_HOME=%CCCC_NATIVE_HOME% && set MCP_API_KEY=local-dev-key-12345 && python api_server.py"

timeout /t 2 /nobreak >nul

echo [6/6] Starting dev UI on %WEB_DEV_PORT%...
start "CCCC Test Web" cmd /k "cd /d %PROJECT_ROOT%\cccc_medical-main\web && set CCCC_WEB_HOST=%CCCC_WEB_HOST% && set CCCC_WEB_PORT=%CCCC_WEB_PORT% && npm run dev -- --host 127.0.0.1 --port %WEB_DEV_PORT% --strictPort"

echo.
echo Open:
echo   Dev UI:   http://127.0.0.1:%WEB_DEV_PORT%/ui/
echo   CCCC UI:  http://127.0.0.1:%CCCC_WEB_PORT%/ui/
echo   API:      http://127.0.0.1:8001/
echo   Memory:   http://127.0.0.1:%MEMORY_PALACE_PORT%/health
echo.
echo Isolated runtime home:
echo   %CCCC_HOME%
echo.
echo The default runtime at C:\Users\Administrator\.cccc is not used.
echo.
pause

goto :eof

:kill_port
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /r /c:":%~1 .*LISTENING"') do (
    taskkill /PID %%P /F >nul 2>nul
)
exit /b 0

:wait_http_ready
set "WAIT_URL=%~1"
set "WAIT_RETRIES=%~2"
if "%WAIT_RETRIES%"=="" set "WAIT_RETRIES=30"
set /a WAIT_COUNT=0
:wait_http_ready_loop
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; try { $resp = Invoke-WebRequest -UseBasicParsing '%WAIT_URL%'; if ($resp.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 exit /b 0
set /a WAIT_COUNT+=1
if %WAIT_COUNT% GEQ %WAIT_RETRIES% exit /b 1
timeout /t 1 /nobreak >nul
goto :wait_http_ready_loop
