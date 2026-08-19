FROM python:3.13-slim

# 统一 HuggingFace 缓存目录到 /app/hf_home
# 后续在 docker-compose 中把宿主机目录挂载到 /app/hf_home 即可持久化模型缓存，
# 避免每次启动重新下载 BAAI 模型。
ENV HF_HOME=/app/hf_home \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先装 CPU 版 PyTorch（体积远小于默认的 CUDA 版），再装其余依赖
RUN pip install --no-cache-dir torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
