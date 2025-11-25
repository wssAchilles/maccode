# =============================================================================
# 数据科学后端 Docker 镜像
# 基于 Python 3.11-slim，支持 Flask + Gurobi + Firebase + Scikit-learn
# =============================================================================

# Stage 1: 构建阶段 - 安装依赖
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装构建依赖
# - gcc, g++: 编译 C/C++ 扩展 (numpy, scipy, scikit-learn)
# - libffi-dev: Foreign Function Interface，Firebase SDK 需要
# - libxml2-dev, libxslt-dev: lxml 库依赖 (gridstatus 需要)
# - curl: 健康检查和调试
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .

# 安装 Python 依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级 pip 并安装依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: 运行阶段 - 最小化镜像
# =============================================================================
FROM python:3.11-slim AS runtime

# 元数据标签
LABEL maintainer="Achilles <achilles@example.com>"
LABEL description="Data Science Backend API - Flask + Gurobi + Firebase"
LABEL version="1.0.0"

# 设置工作目录
WORKDIR /app

# 安装运行时依赖（只保留必要的库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY . .

# 创建非 root 用户运行应用（安全最佳实践）
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# =============================================================================
# 环境变量配置
# =============================================================================

# Flask 配置
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Gurobi WLS 许可证变量（运行时通过 -e 或 .env 文件传入）
# 注意：不要在 Dockerfile 中硬编码这些值！
# GRB_WLSACCESSID - WLS Access ID
# GRB_WLSSECRET   - WLS Secret Key  
# GRB_LICENSEID   - License ID

# GCP/Firebase 配置（运行时传入）
# GCP_PROJECT_ID
# STORAGE_BUCKET_NAME
# GOOGLE_APPLICATION_CREDENTIALS (指向挂载的服务账号密钥)

# 端口配置
ENV PORT=8080
EXPOSE 8080

# =============================================================================
# 健康检查
# =============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# =============================================================================
# 启动命令
# =============================================================================
# 使用 gunicorn 启动 Flask 应用
# --bind 0.0.0.0:8080  : 绑定所有网络接口
# --timeout 300        : 5分钟超时（适合长时间运行的优化任务）
# --workers 2          : 2个工作进程（可根据容器资源调整）
# --threads 2          : 每个工作进程2个线程
# --access-logfile -   : 访问日志输出到 stdout
# --error-logfile -    : 错误日志输出到 stderr
CMD ["gunicorn", \
    "--bind", "0.0.0.0:8080", \
    "--timeout", "300", \
    "--workers", "2", \
    "--threads", "2", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "main:app"]
