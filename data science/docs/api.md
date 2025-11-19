# API 文档

## 基础信息

- **Base URL**: `https://your-project.appspot.com`
- **认证方式**: Bearer Token (Firebase ID Token)

## 认证

所有需要认证的接口都需要在请求头中携带:

```
Authorization: Bearer <firebase-id-token>
```

## API 端点

### 1. 健康检查

```http
GET /health
```

**响应**
```json
{
  "status": "ok",
  "timestamp": "2025-11-17T00:00:00Z"
}
```

---

### 2. 用户信息

```http
GET /api/user/profile
```

**需要认证**: ✅

**响应**
```json
{
  "uid": "user-id",
  "email": "user@example.com",
  "displayName": "User Name"
}
```

---

### 3. 数据上传

```http
POST /api/data/upload
```

**需要认证**: ✅

**请求体**
```json
{
  "fileName": "dataset.csv",
  "data": "base64-encoded-data"
}
```

**响应**
```json
{
  "success": true,
  "fileUrl": "gs://bucket/path/to/file",
  "uploadedAt": "2025-11-17T00:00:00Z"
}
```

---

### 4. 模型预测

```http
POST /api/model/predict
```

**需要认证**: ✅

**请求体**
```json
{
  "modelId": "model-name",
  "input": {
    "feature1": 1.0,
    "feature2": 2.0
  }
}
```

**响应**
```json
{
  "prediction": 0.95,
  "confidence": 0.87,
  "timestamp": "2025-11-17T00:00:00Z"
}
```

---

## 错误响应

所有错误响应格式统一为:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述"
  }
}
```

### 常见错误码

| 状态码 | 错误码 | 描述 |
|--------|--------|------|
| 400 | BAD_REQUEST | 请求参数错误 |
| 401 | UNAUTHORIZED | 未认证或 Token 无效 |
| 403 | FORBIDDEN | 无权限访问 |
| 404 | NOT_FOUND | 资源不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |
