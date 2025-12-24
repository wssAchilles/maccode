# ============================================
# SentinEL Traffic Simulator Dockerfile
# 轻量级负载生成器容器
# ============================================

FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装依赖
RUN pip install --no-cache-dir requests

# 复制脚本
COPY traffic_gen.py .

# 启动命令
CMD ["python", "traffic_gen.py"]
