@echo off
cd /d "%~dp0"
py -3 gui_client.py
if errorlevel 1 pause
