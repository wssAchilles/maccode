# ============================================
# SentinEL Backend Dockerfile
# 基于 Python 3.11-slim 的 FastAPI 微服务容器
# ============================================

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# - PYTHONDONTWRITEBYTECODE: 防止生成 .pyc 文件
# - PYTHONUNBUFFERED: 确保日志实时输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装系统依赖 (如果需要构建 C 扩展)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .

# 使用 --no-cache-dir 减小镜像体积
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# Cloud Run 强制要求: 监听 $PORT 环境变量
# 默认端口 8080，Cloud Run 会自动注入 PORT 环境变量
ENV PORT=8080

# 暴露端口 (文档用途)
EXPOSE 8080

# 启动命令 - 使用 shell 形式以支持环境变量展开
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
