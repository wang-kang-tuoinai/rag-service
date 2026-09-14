@echo off
chcp 65001 >nul
echo 正在启动 RAG 检索服务...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
uvicorn main:app --host 0.0.0.0 --port 8000
pause
