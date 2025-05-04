@echo off
echo ----------------------------------------------
echo MetaStream Aggregator - Installation and Setup
echo ----------------------------------------------

REM Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.9 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check Python version (need 3.9+)
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%V"
for /f "tokens=1,2 delims=." %%A in ("%PYTHON_VERSION%") do (
    set "PYTHON_MAJOR=%%A"
    set "PYTHON_MINOR=%%B"
)

if %PYTHON_MAJOR% LSS 3 (
    echo Python 3.9 or higher is required. You have Python %PYTHON_VERSION%.
    pause
    exit /b 1
)
if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 9 (
    echo Python 3.9 or higher is required. You have Python %PYTHON_VERSION%.
    pause
    exit /b 1
)

echo Python %PYTHON_VERSION% detected.

REM Create virtual environment if it doesn't exist
if not exist venv\ (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment and install dependencies
echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Install requirements
if exist requirements.txt (
    echo Installing requirements from requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Failed to install requirements.
        call venv\Scripts\deactivate.bat
        pause
        exit /b 1
    )
) else (
    echo Installing required packages...
    pip install Flask requests beautifulsoup4 lxml google-api-python-client
    if %errorlevel% neq 0 (
        echo Failed to install required packages.
        call venv\Scripts\deactivate.bat
        pause
        exit /b 1
    )
)

REM Create sample files if they don't exist
if not exist sites.json (
    if exist sites.example.json (
        echo Creating sites.json from example...
        copy sites.example.json sites.json > nul
    ) else (
        echo Warning: sites.example.json not found. You will need to create sites.json manually.
    )
)

if not exist settings.json (
    if exist settings.example.json (
        echo Creating settings.json from example...
        copy settings.example.json settings.json > nul
    ) else (
        echo Warning: settings.example.json not found. You will need to create settings.json manually.
    )
)

REM Create cache directory if it doesn't exist
if not exist search_cache mkdir search_cache

echo.
echo ---------------------------------------------------
echo Installation complete! Starting MetaStream Aggregator...
echo ---------------------------------------------------
echo.
echo The application will be available at: http://127.0.0.1:8001
echo Press Ctrl+C to stop the server when you're done.
echo.

REM Start the Flask application
python app.py

REM Deactivate virtual environment when the application exits
call venv\Scripts\deactivate.bat

pause