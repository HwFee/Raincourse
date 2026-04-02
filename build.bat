@echo off
setlocal
cd /d "%~dp0"

echo ====================================
echo Raincourse AI Helper - Build Script
echo ====================================
echo.

set "PY_CMD=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe"
if not exist "%PY_CMD%" (
    where py >nul 2>nul
    if "%ERRORLEVEL%"=="0" (
        set "PY_CMD=py -3"
    ) else (
        where python >nul 2>nul
        if "%ERRORLEVEL%"=="0" (
            set "PY_CMD=python"
        ) else (
            echo [ERROR] Python interpreter not found.
            pause
            exit /b 1
        )
    )
)

echo [1/4] Installing dependencies...
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.
    pause
    exit /b 1
)
echo [OK] Dependencies installed

echo.
echo [2/4] Cleaning old build files...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
echo [OK] Cleaned

echo.
echo [3/4] Building EXE...
%PY_CMD% -m PyInstaller build.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [4/4] Validating output...
if not exist "dist\RaincourseAIHelper.exe" (
    echo [ERROR] Build finished but dist\RaincourseAIHelper.exe not found.
    pause
    exit /b 1
)

echo.
echo ====================================
echo [SUCCESS] Build completed!
echo ====================================
echo Output: dist\RaincourseAIHelper.exe
echo.
echo Press any key to open output directory...
pause >nul
explorer dist
