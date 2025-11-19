# 数据科学课程设计项目

## 📋 项目概述

这是一个基于 Flutter + Python + Google Cloud Platform 的数据科学应用项目。

## 🛠️ 技术栈

### 前端
- **框架**: Flutter Web
- **部署**: Firebase Hosting
- **认证**: Firebase Authentication
- **状态管理**: (待定)

### 后端
- **框架**: Flask (Python 3.11)
- **部署**: Google App Engine (GAE)
- **存储**: Google Cloud Storage
- **认证**: Firebase Admin SDK

### 数据科学
- **数据处理**: pandas, numpy
- **机器学习**: scikit-learn
- **深度学习**: (待定)

## 📁 项目结构

```
.
├── back/               # 后端服务 (Python/Flask)
│   ├── api/           # API 路由
│   ├── services/      # 业务逻辑
│   ├── models/        # 机器学习模型
│   ├── utils/         # 工具函数
│   └── tests/         # 测试文件
│
├── front/             # 前端应用 (Flutter)
│   ├── lib/
│   │   ├── screens/   # 页面
│   │   ├── services/  # 服务层
│   │   ├── models/    # 数据模型
│   │   └── widgets/   # 可复用组件
│   └── assets/        # 静态资源
│
├── data/              # 数据文件
│   ├── raw/          # 原始数据
│   ├── processed/    # 处理后的数据
│   └── models/       # 训练好的模型
│
├── docs/              # 项目文档
└── scripts/           # 部署和工具脚本
```

## 🚀 快速开始

### 环境准备

1. **安装依赖**
   ```bash
   # 后端
   cd back
   pip install -r requirements.txt
   
   # 前端
   cd front
   flutter pub get
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入实际配置
   ```

### 本地开发

#### 后端开发
```bash
cd back
python main.py
```

#### 前端开发
```bash
cd front
flutter run -d chrome
```

## 📦 部署

### 部署后端到 GAE
```bash
cd back
gcloud app deploy
```

### 部署前端到 Firebase Hosting
```bash
cd front
flutter build web
firebase deploy --only hosting
```

## 📝 开发规范

- 遵循 PEP 8 代码规范 (Python)
- 遵循 Dart 官方代码规范 (Flutter)
- 提交前确保代码通过测试
- 使用有意义的提交信息

## 🔒 安全注意事项

- 不要提交 `.env` 文件
- 不要提交 GCP 服务账号密钥
- 不要提交 Firebase 配置文件中的敏感信息

## 📚 相关文档

- [Flutter 文档](https://flutter.dev/docs)
- [Firebase 文档](https://firebase.google.com/docs)
- [Google Cloud 文档](https://cloud.google.com/docs)
- [Flask 文档](https://flask.palletsprojects.com/)

## 👥 团队成员

- (待添加)

## 📄 许可证

(待定)
