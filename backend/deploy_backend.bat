REM deployment script for windows systems
@echo off

REM install necessary libraries
python -m pip install -r requirements.txt

REM start REST API
start /b python app.py

REM start reading from serial connection
python core.py