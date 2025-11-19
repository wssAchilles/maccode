# 前后端打通指南

## 📋 架构概览

```
Flutter Web (前端)          Flask API (后端)
    ↓                           ↓
Firebase Auth  ←→  Token  ←→  Firebase Admin SDK
    ↓                           ↓
HTTP Client    →   API 请求  →  Flask Routes
    ↓                           ↓
获取响应       ←   JSON 数据  ←  业务逻辑
```

## 🔑 认证流程

### 步骤 1: 用户在前端登录
1. 用户使用 Firebase Auth 登录 (邮箱/Google/其他)
2. 前端获取 Firebase ID Token
3. 前端存储 Token 供后续 API 调用使用

### 步骤 2: 前端调用后端 API
1. 前端在请求头中携带 ID Token
2. 发送 HTTP 请求到后端 API

### 步骤 3: 后端验证 Token
1. 后端接收请求,提取 Token
2. 使用 Firebase Admin SDK 验证 Token
3. 验证成功后处理业务逻辑
4. 返回 JSON 响应

## 🔧 实现步骤

### 1. 后端配置 (Flask + Firebase Admin)

#### 1.1 安装依赖
后端 `requirements.txt` 已包含必要依赖:
- `Flask` - Web 框架
- `flask-cors` - 处理跨域请求
- `firebase-admin` - Firebase 服务端 SDK
- `google-cloud-storage` - Cloud Storage 操作

#### 1.2 初始化 Firebase Admin SDK
在后端创建 Firebase Admin 初始化代码

#### 1.3 创建认证中间件
验证每个请求的 Firebase Token

#### 1.4 创建 API 端点
实现业务逻辑 API

### 2. 前端配置 (Flutter + HTTP Client)

#### 2.1 安装依赖
在 `pubspec.yaml` 中添加:
- `firebase_core` - Firebase 核心
- `firebase_auth` - Firebase 认证
- `http` - HTTP 客户端

#### 2.2 初始化 Firebase
在应用启动时初始化

#### 2.3 创建 API Service
封装所有 API 调用逻辑

#### 2.4 创建 Auth Service
管理用户登录状态

## 🌐 API 调用示例

### 前端发送请求
```dart
// 1. 获取当前用户的 ID Token
String? token = await FirebaseAuth.instance.currentUser?.getIdToken();

// 2. 设置请求头
Map<String, String> headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer $token',
};

// 3. 发送请求
var response = await http.post(
  Uri.parse('https://your-project.appspot.com/api/data/upload'),
  headers: headers,
  body: jsonEncode({'data': 'your-data'}),
);
```

### 后端处理请求
```python
# 1. 从请求头提取 Token
token = request.headers.get('Authorization', '').replace('Bearer ', '')

# 2. 验证 Token
decoded_token = auth.verify_id_token(token)
user_id = decoded_token['uid']

# 3. 处理业务逻辑
# 4. 返回 JSON 响应
return jsonify({'success': True, 'data': result})
```

## 🔒 CORS 配置

后端需要允许前端域名的跨域请求:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=[
    'https://your-project.web.app',      # Firebase Hosting
    'http://localhost:*',                 # 本地开发
])
```

## 🚀 部署后的 URL

### 开发环境
- 前端: `http://localhost:port`
- 后端: `http://localhost:8080`

### 生产环境
- 前端: `https://your-project.web.app` (Firebase Hosting)
- 后端: `https://your-project.appspot.com` (GAE)

## 📝 配置清单

- [ ] 后端安装 `flask-cors` 依赖
- [ ] 后端配置 Firebase Admin SDK
- [ ] 后端实现认证中间件
- [ ] 后端创建 API 路由
- [ ] 前端添加 `http` 依赖
- [ ] 前端初始化 Firebase
- [ ] 前端创建 API Service
- [ ] 前端创建 Auth Service
- [ ] 配置 CORS 允许前端域名
- [ ] 更新 `.env` 文件配置后端 URL

## 🧪 测试流程

1. **本地测试**
   - 启动后端: `cd back && python main.py`
   - 启动前端: `cd front && flutter run -d chrome`
   - 测试登录和 API 调用

2. **部署测试**
   - 部署后端到 GAE
   - 部署前端到 Firebase Hosting
   - 测试生产环境的完整流程

## ⚠️ 常见问题

### 1. CORS 错误
**问题**: 前端无法调用后端 API
**解决**: 确保后端配置了 `flask-cors` 并允许前端域名

### 2. Token 验证失败
**问题**: 后端返回 401 未授权
**解决**: 检查前端是否正确发送 Token,后端是否正确验证

### 3. 本地开发连接问题
**问题**: 前端无法连接本地后端
**解决**: 使用 `http://localhost:8080` 而不是 `127.0.0.1`

## 📚 下一步

完成前后端打通后,你可以:
1. 实现数据上传功能
2. 实现模型训练和预测 API
3. 添加数据可视化功能
4. 优化用户体验
