@echo off
echo Starting Flask Development Server...
call .\venv\Scripts\activate
set FLASK_APP=app.py
set FLASK_ENV=development
flask run --port 5000
pause
