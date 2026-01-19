@echo off
echo Starting Production Management System...
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated.
    echo.
)

REM Start the Flask application
echo Starting Flask server on http://localhost:5000
echo.
python app.py

pause
