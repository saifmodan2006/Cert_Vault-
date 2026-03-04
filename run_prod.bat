@echo off
echo Starting Waitress Production Server on http://localhost:8000...
call .\venv\Scripts\activate
pip install waitress
waitress-serve --listen=0.0.0.0:8000 wsgi:application
pause
