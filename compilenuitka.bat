@echo off
rem Build a standalone DbBasic executable with Nuitka (Windows) and install it.
rem
rem Usage: compilenuitka.bat [install_dir]
rem   install_dir defaults to %USERPROFILE%\bin (add it to PATH to run dbbasic anywhere)
rem   Set PYTHON to use a particular Python (default: python).
rem   Needs: pip install -r requirements.txt -r requirements-build.txt
setlocal

set "REPO_DIR=%~dp0"
set "SRC_DIR=%REPO_DIR%src"
set "BUILD_DIR=%REPO_DIR%build"
set "INSTALL_DIR=%~1"
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=%USERPROFILE%\bin"
if "%PYTHON%"=="" set "PYTHON=python"

rem Unpack once into a per-build cache folder instead of a fresh temp folder
rem on every launch (otherwise each run pays several seconds of extraction).
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddHHmmss"') do set "BUILD_ID=%%i"
if "%BUILD_ID%"=="" set "BUILD_ID=%RANDOM%%RANDOM%"

rem The compiled program can't read its own source, so it relies on
rem Interpreter.BUILTIN_FN_NAMES for function references; make sure it's current.
"%PYTHON%" "%REPO_DIR%tools\check_builtin_names.py"
if errorlevel 1 exit /b 1
rem The build bundles the DuckDB this Python has: stop if it is too old (or numpy is missing).
"%PYTHON%" "%REPO_DIR%tools\check_dependencies.py"
if errorlevel 1 exit /b 1

pushd "%SRC_DIR%" || exit /b 1
"%PYTHON%" -m nuitka ^
    --onefile ^
    --onefile-tempdir-spec="{CACHE_DIR}/dbbasic/%BUILD_ID%" ^
    --follow-imports ^
    --assume-yes-for-downloads ^
    --output-dir="%BUILD_DIR%" ^
    --output-filename=dbbasic.exe ^
    dbbasic.py
set "BUILD_STATUS=%ERRORLEVEL%"
popd
if not "%BUILD_STATUS%"=="0" (
    echo Build failed.
    exit /b %BUILD_STATUS%
)

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /y "%BUILD_DIR%\dbbasic.exe" "%INSTALL_DIR%\dbbasic.exe" >nul
if errorlevel 1 (
    echo Could not copy dbbasic.exe to %INSTALL_DIR%
    exit /b 1
)
echo Installed: %INSTALL_DIR%\dbbasic.exe
