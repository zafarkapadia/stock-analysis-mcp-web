@echo off
:: Navigate to your project folder
cd /d "C:\Users\zafar\Documents\Carnegie Mellon Course\examples\stock-analysis-mcp-web\jobs"

:: Force Python UTF-8 environment variable to prevent emoji crashes
set PYTHONUTF8=1

:: Call Python directly from your specific virtual environment and run the pipeline
"..\.venvstockanalysisweb\Scripts\python.exe" download-articles.py

exit
