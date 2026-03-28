@echo off
title Energy Management Server

echo ================================
echo  Energy Management System
echo ================================
echo.

cd /d D:\8th Sem\BTP II\btp\BTP_II

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Checking Python...
where python
python --version

echo.
echo Starting server...
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause