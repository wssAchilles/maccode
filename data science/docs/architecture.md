# 系统架构设计

## 整体架构

```
┌─────────────────┐
│   用户浏览器     │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────┐
│  Firebase Hosting (前端)     │
│  - Flutter Web               │
│  - Firebase Auth (客户端)    │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│  Google App Engine (后端)    │
│  - Flask API                 │
│  - Firebase Admin SDK        │
└────────┬────────────────────┘
         │
         ↓
┌─────────────────────────────┐
│  Google Cloud Storage        │
│  - 数据集存储                 │
│  - 模型文件存储               │
└─────────────────────────────┘
```

## 认证流程

1. 用户在前端通过 Firebase Auth 登录
2. 前端获取 ID Token
3. 前端调用后端 API 时携带 ID Token
4. 后端使用 Firebase Admin SDK 验证 Token
5. 验证成功后处理请求

## 数据流

1. **数据上传**: 前端 → Cloud Storage
2. **数据处理**: 后端从 Cloud Storage 读取 → 处理 → 存回
3. **模型训练**: 后端从 Cloud Storage 读取数据 → 训练 → 保存模型
4. **模型预测**: 后端加载模型 → 预测 → 返回结果

## 技术选型理由

### Firebase Hosting
- 全球 CDN 加速
- 自动 HTTPS
- 免费额度充足
- 与 Firebase Auth 无缝集成

### Google App Engine
- 自动扩缩容
- 免运维
- 适合 Python 后端
- 与 GCP 服务集成良好

### Cloud Storage
- 高可用性
- 适合存储大文件
- 支持分层存储降低成本

### Firebase Auth
- 前后端统一认证
- 支持多种登录方式
- 安全可靠
