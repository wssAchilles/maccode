# 🚀 前后端打通完整部署指南

## 🎯 目标架构

```
用户浏览器
    ↓
https://data-science-44398.web.app (Firebase Hosting)
    ↓ (携带 Firebase ID Token)
https://data-science-44398.an.r.appspot.com (GAE - 自动唤醒)
    ↓ (验证 Token + 分析数据)
返回分析结果
```

## ✅ 已实现的功能

### 后端 (GAE)

- ✅ **自动唤醒机制**：GAE 在休眠状态，收到请求时自动启动
- ✅ **Firebase 认证验证**：所有 API 必须携带有效的 ID Token
- ✅ **CSV 数据分析**：使用 Pandas 进行描述性统计分析
- ✅ **Excel 支持**：支持 .xlsx 和 .xls 格式
- ✅ **Cloud Storage 归档**：可选择性保存文件到 Cloud Storage
- ✅ **CORS 严格限制**：只允许指定的前端域名访问
- ✅ **API 限流**：防止滥用（20次/分钟）
- ✅ **结构化日志**：记录所有请求和错误

### 前端 (Flutter Web)

- ✅ **Google 登录**：使用 Firebase Auth + Google Sign-In
- ✅ **文件选择器**：支持选择 CSV 文件
- ✅ **安全通信**：自动附加 Authorization 头部
- ✅ **加载状态**：显示 GAE 唤醒等待动画
- ✅ **结果展示**：美观的表格和统计信息展示
- ✅ **错误处理**：友好的错误提示

## 📋 部署前准备

### 1. GCP 项目设置

确保你的 GCP 项目已启用以下 API：

```bash
gcloud services enable appengine.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable firestore.googleapis.com
```

### 2. Firebase 项目设置

1. 前往 [Firebase Console](https://console.firebase.google.com/)
2. 选择项目 `data-science-44398`
3. 启用 **Authentication** → **Google** 登录方式
4. 添加授权域名：
   - `data-science-44398.web.app`
   - `data-science-44398.firebaseapp.com`
   - `localhost` (开发环境)

## 🎬 部署步骤

### 步骤 1：部署后端到 GAE

```bash
# 1. 进入后端目录
cd back

# 2. 确认 app.yaml 配置正确
cat app.yaml

# 3. 部署到 GAE
gcloud app deploy

# 4. 确认部署成功
gcloud app browse
```

**app.yaml 关键配置：**

```yaml
runtime: python311
entrypoint: gunicorn -b :$PORT main:app

instance_class: F1  # 最小实例，节省成本

automatic_scaling:
  min_instances: 0  # 允许完全休眠
  max_instances: 5
  target_cpu_utilization: 0.65

env_variables:
  FLASK_ENV: 'production'
```

### 步骤 2：部署前端到 Firebase Hosting

```bash
# 1. 进入前端目录
cd front

# 2. 获取依赖
flutter pub get

# 3. 构建 Web 应用
flutter build web --release

# 4. 部署到 Firebase Hosting
firebase deploy --only hosting

# 5. 访问生产 URL
# https://data-science-44398.web.app
```

### 步骤 3：验证部署

#### 测试后端

```bash
# 测试健康检查（无需认证）
curl https://data-science-44398.an.r.appspot.com/health

# 测试支持的格式（无需认证）
curl https://data-science-44398.an.r.appspot.com/api/analysis/supported-formats
```

预期响应：

```json
{
  "status": "ok",
  "timestamp": "2025-11-17T..."
}
```

#### 测试前端

1. 访问 <https://data-science-44398.web.app>
2. 点击 "使用 Google 登录"
3. 选择一个 CSV 文件
4. 点击 "开始分析"
5. 等待 5-10 秒（首次唤醒 GAE）
6. 查看分析结果

## 🔒 安全性验证

### CORS 配置

生产环境的 CORS 配置只允许指定域名：

```python
# back/config.py
CORS_ORIGINS = [
    'https://data-science-44398.web.app',
    'https://data-science-44398.firebaseapp.com',
]
```

测试 CORS：

```bash
curl -H "Origin: https://evil-site.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     https://data-science-44398.an.r.appspot.com/api/analysis/analyze-csv
```

应该返回 CORS 错误或不包含 `Access-Control-Allow-Origin` 头部。

### Token 验证

未认证的请求会被拒绝：

```bash
curl -X POST \
     https://data-science-44398.an.r.appspot.com/api/analysis/analyze-csv

# 预期响应：401 Unauthorized
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing or invalid Authorization header"
  }
}
```

## 📊 监控和日志

### 查看 GAE 日志

```bash
# 查看最近的日志
gcloud app logs tail -s default

# 查看特定时间段的日志
gcloud app logs read --limit=50
```

### 查看 Firebase Hosting 日志

在 Firebase Console → Hosting → Usage 标签查看访问统计。

### 重要指标

1. **GAE 冷启动时间**：首次请求响应时间（通常 5-10 秒）
2. **分析处理时间**：Pandas 分析耗时
3. **错误率**：401/403/500 错误数量
4. **请求量**：每日 API 调用次数

## 💰 成本估算

### Firebase Hosting（免费层）

- 存储：10 GB
- 传输：360 MB/天
- 对于这个项目：**完全免费**

### GAE（按需付费）

- F1 实例：$0.05/小时（仅运行时计费）
- 最小实例数：0（完全休眠）
- 预计成本：**$0-5/月**（取决于使用量）

### Cloud Storage（按需付费）

- 存储：$0.02/GB/月
- 操作：$0.005/万次
- 预计成本：**$0-1/月**

**总计**：每月约 **$0-6**（低使用量情况下接近免费）

## 🔧 常见问题

### Q1: GAE 首次响应很慢？

**A**: 这是正常的冷启动。GAE 从休眠状态唤醒需要 5-10 秒。可以：

- 设置 `min_instances: 1` 保持一个实例始终运行（增加成本）
- 或者在前端显示"唤醒中"的提示

### Q2: CORS 错误？

**A**: 检查：

1. 后端 `config.py` 中的 `CORS_ORIGINS` 配置
2. Firebase Hosting 的实际域名是否匹配
3. 浏览器控制台的具体错误信息

### Q3: 401 Unauthorized 错误？

**A**: 检查：

1. 用户是否已登录（`FirebaseAuth.instance.currentUser`）
2. Token 是否正确获取（`await user.getIdToken()`）
3. Authorization 头部格式：`Bearer <token>`
4. Firebase Admin SDK 是否在后端正确初始化

### Q4: 文件太大无法上传？

**A**: 默认限制 50MB。可以调整：

- 前端：`file_picker` 配置
- 后端：`validators.py` 中的 `max_size_mb` 参数
- GAE：`app.yaml` 中的 `max_request_size`

### Q5: 如何支持更多文件格式？

**A**:

1. 后端：在 `analysis_service.py` 添加新的分析方法
2. 后端：在 `analysis.py` 添加新的路由
3. 前端：更新 `file_picker` 的 `allowedExtensions`

## 🚀 性能优化

### 后端优化

1. **启用缓存**：

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def analyze_cached(file_hash, uid):
    # 缓存分析结果
    pass
```

2. **异步处理**：

```python
from flask import g
import threading

def async_save_to_storage(file, path):
    thread = threading.Thread(
        target=StorageService.upload_file,
        args=(file, path)
    )
    thread.start()
```

3. **数据库索引**（如果使用 Firestore）：

```python
# 为频繁查询的字段创建索引
db.collection('analyses').where('uid', '==', uid).order_by('timestamp')
```

### 前端优化

1. **懒加载**：

```dart
import 'package:flutter/widgets.dart' deferred as widgets;
```

2. **图片优化**：压缩和使用 WebP 格式

3. **代码分割**：将大型组件拆分为独立模块

## 📱 下一步扩展

### 功能扩展

1. **更多分析类型**：
   - 时间序列分析
   - 相关性分析
   - 聚类分析
   - 回归分析

2. **可视化**：
   - 集成 Chart.js 或 Plotly
   - 生成图表并返回

3. **批量处理**：
   - 支持上传多个文件
   - 异步处理队列

4. **历史记录**：
   - 使用 Firestore 存储分析历史
   - 用户可以查看过往分析

### 架构扩展

1. **微服务化**：
   - 数据处理服务
   - ML 训练服务
   - 报告生成服务

2. **实时通知**：
   - 使用 Firebase Cloud Messaging
   - WebSocket 连接

3. **API 版本管理**：
   - `/api/v1/`
   - `/api/v2/`

## 📚 相关资源

- [GAE Python 文档](https://cloud.google.com/appengine/docs/standard/python3)
- [Firebase Hosting 文档](https://firebase.google.com/docs/hosting)
- [Flutter Web 部署](https://flutter.dev/docs/deployment/web)
- [Pandas 文档](https://pandas.pydata.org/docs/)

## ✅ 部署检查清单

- [ ] GCP 项目已创建并启用 API
- [ ] Firebase 项目已配置认证
- [ ] 后端 `app.yaml` 配置正确
- [ ] 后端 `requirements.txt` 包含所有依赖
- [ ] CORS 配置包含正确的域名
- [ ] 前端 `firebase.json` 配置正确
- [ ] 前端已构建（`flutter build web`）
- [ ] 后端已部署到 GAE
- [ ] 前端已部署到 Firebase Hosting
- [ ] 可以成功登录
- [ ] 可以上传并分析文件
- [ ] 日志记录正常工作

---

## 🎉 恭喜

你的数据科学即服务应用已经成功打通前后端！

**生产 URL**: <https://data-science-44398.web.app>

现在你可以：

1. 随时随地打开这个网址
2. 使用 Google 账号登录
3. 上传 CSV 文件进行分析
4. GAE 会自动唤醒并处理请求
5. 无需手动启动任何服务器！

**享受你的按需数据科学服务吧！** 🚀📊
