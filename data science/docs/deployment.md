# 部署指南

## 前置准备

### 1. GCP 项目设置

```bash
# 登录 GCP
gcloud auth login

# 设置项目
gcloud config set project YOUR_PROJECT_ID

# 启用必要的 API
gcloud services enable appengine.googleapis.com
gcloud services enable storage.googleapis.com
```

### 2. Firebase 项目设置

```bash
# 安装 Firebase CLI
npm install -g firebase-tools

# 登录 Firebase
firebase login

# 初始化项目
cd front
firebase init hosting
```

## 后端部署 (GAE)

### 开发环境部署

```bash
cd back

# 安装依赖
pip install -r requirements.txt

# 本地测试
python main.py

# 部署到 GAE
gcloud app deploy
```

### 查看日志

```bash
gcloud app logs tail -s default
```

## 前端部署 (Firebase Hosting)

### 构建和部署

```bash
cd front

# 安装依赖
flutter pub get

# 构建 Web 版本
flutter build web --release

# 部署到 Firebase Hosting
firebase deploy --only hosting
```

### 预览部署

```bash
# 创建预览部署 (不会影响生产环境)
firebase hosting:channel:deploy preview
```

## 环境变量配置

### 后端环境变量 (GAE)

在 `app.yaml` 中添加:

```yaml
env_variables:
  GCP_PROJECT_ID: "your-project-id"
  STORAGE_BUCKET_NAME: "your-bucket-name"
```

### 前端环境变量

在 Firebase Hosting 中使用构建时环境变量。

## Cloud Storage 设置

```bash
# 创建存储桶
gsutil mb gs://your-bucket-name

# 设置 CORS
gsutil cors set cors.json gs://your-bucket-name
```

## 监控和日志

### GAE 监控

- 访问: https://console.cloud.google.com/appengine
- 查看实例、请求、错误等信息

### Firebase Hosting 监控

- 访问: https://console.firebase.google.com
- 查看部署历史、流量统计

## 回滚

### 回滚 GAE 部署

```bash
# 查看版本
gcloud app versions list

# 切换到旧版本
gcloud app versions migrate OLD_VERSION
```

### 回滚 Firebase Hosting 部署

```bash
# 查看部署历史
firebase hosting:clone SOURCE_SITE_ID:SOURCE_CHANNEL_ID TARGET_SITE_ID:live
```

## 成本优化

1. **GAE**: 设置 `min_instances: 0` 避免空闲计费
2. **Cloud Storage**: 使用生命周期管理自动删除旧文件
3. **Firebase**: 利用免费额度,监控使用量

## 安全检查清单

- [ ] 所有 API 端点都需要认证
- [ ] 敏感信息不在代码中硬编码
- [ ] 使用 HTTPS
- [ ] 定期更新依赖
- [ ] 设置 CORS 策略
- [ ] 启用 Cloud Armor (可选)
