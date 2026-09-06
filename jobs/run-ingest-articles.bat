@echo off
:: Navigate to your project folder
cd /d "<Link to Jobs folder>"

:: Force Python UTF-8 environment variable to prevent emoji crashes
set PYTHONUTF8=1

:: Call Python directly from your specific virtual environment and run the pipeline
"..\.venvstockanalysisweb\Scripts\python.exe" download-articles.py

exit
