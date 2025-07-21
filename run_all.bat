@echo off

REM wscript.exe .\scripts\run_all.vbs

if not exist logs mkdir logs

start /b /wait cmd /c "python src\document_parsing.py > logs\document_parsing.log 2>&1"
start /b /wait cmd /c "python src\alias_grouper.py > logs\alias_grouper.log 2>&1"
start /b /wait cmd /c "python src\graph_creation.py > logs\graph_creation.log 2>&1"

echo All scripts completed.
pause
