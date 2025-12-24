# ============================================
# SentinEL Frontend Dockerfile
# 多阶段构建 (Multi-stage Build) - 工业级优化
# 最终镜像体积: ~150MB (vs ~1GB 未优化)
# ============================================

# ============================================
# Stage 1: 依赖安装 (deps)
# ============================================
FROM node:20-alpine AS deps

# 安装 libc6-compat 以支持某些原生模块
RUN apk add --no-cache libc6-compat

WORKDIR /app

# 复制 package 文件
COPY package.json package-lock.json* ./

# 安装依赖 (使用 ci 确保锁文件一致性)
RUN npm ci --legacy-peer-deps

# ============================================
# Stage 2: 构建应用 (builder)
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

# 从 deps 阶段复制 node_modules
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 接收构建时环境变量 (NEXT_PUBLIC_* 需要在构建时注入)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# 禁用 Next.js 遥测
ENV NEXT_TELEMETRY_DISABLED=1

# 构建项目 (standalone 模式)
RUN npm run build

# ============================================
# Stage 3: 生产运行环境 (runner)
# ============================================
FROM node:20-alpine AS runner

WORKDIR /app

# 安全性: 创建非 root 用户运行应用
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# 设置生产环境
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# 从 builder 阶段复制 standalone 输出
# 注意: standalone 模式会将所有必要文件打包到 .next/standalone
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 切换到非 root 用户
USER nextjs

# Cloud Run 强制要求: 监听 $PORT 环境变量
ENV PORT=3000
EXPOSE 3000

# 启动 standalone 服务器
# 注意: standalone 模式使用内置的 server.js 而非 next start
CMD ["node", "server.js"]
