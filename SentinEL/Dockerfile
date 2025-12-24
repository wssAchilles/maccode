# 使用官方 Python 3.11 轻量级镜像作为基础
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
# 先复制 requirements.txt 可以利用 Docker 缓存层，加速后续构建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有项目代码
COPY . .

# Cloud Run 会通过 PORT 环境变量注入端口号
# 使用 shell 形式以便正确解析 $PORT 环境变量
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
