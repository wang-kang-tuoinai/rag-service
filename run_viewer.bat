@echo off
chcp 65001 >nul
echo 正在启动 Chroma 知识库切片查看器...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run view_chunks.py --server.port 8501
pause
