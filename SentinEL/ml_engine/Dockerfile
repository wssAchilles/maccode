FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY ml_engine/requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn

# 复制源代码 (包含 ml_engine 包)
COPY ml_engine /app/ml_engine

# 复制模型文件
COPY ml_engine/model_artifact /app/model

# 环境变量
ENV PYTHONPATH=/app
ENV AIP_STORAGE_URI=/app/model
ENV AIP_HTTP_PORT=8080

EXPOSE 8080

# 启动服务
CMD ["uvicorn", "ml_engine.serving.serve:app", "--host", "0.0.0.0", "--port", "8080"]
