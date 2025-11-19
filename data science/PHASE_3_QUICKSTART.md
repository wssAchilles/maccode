# 🚀 Phase 3 快速启动指南

## 📋 前置要求

确保已完成：

- ✅ Phase 1 & 2 的所有功能
- ✅ Firebase 项目已创建 (data-science-44398)
- ✅ Firestore 数据库已启用
- ✅ 后端和前端代码已更新

---

## 🔥 Firestore 设置

### 1. 启用 Firestore 数据库

访问 [Firebase Console](https://console.firebase.google.com)

```bash
1. 选择项目: data-science-44398
2. 左侧菜单 > Firestore Database
3. 点击 "创建数据库"
4. 选择区域: asia-northeast1 (东京)
5. 启动模式: 生产模式
6. 点击 "启用"
```

### 2. 配置安全规则

在 Firestore 控制台 > Rules 标签页，添加以下规则：

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 用户历史记录
    match /users/{userId}/history/{recordId} {
      // 只允许用户访问自己的历史记录
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

点击 "发布" 保存规则。

### 3. 创建索引（可选）

在 Firestore 控制台 > Indexes 标签页，添加复合索引：

```
Collection ID: history
Collection group: No
Fields:
  - created_at (Descending)
Query scope: Collection
```

---

## 🖥️ 后端启动

### 1. 安装依赖（如有新依赖）

```bash
cd "/Users/achilles/Documents/code/data science"
source venv/bin/activate
pip install -r back/requirements.txt
```

### 2. 验证配置

检查 `back/config.py`:

```python
GCP_REGION = 'asia-northeast1'  # ✓ 确认
STORAGE_BUCKET_NAME = 'data-science-44398.firebasestorage.app'  # ✓ 确认
```

### 3. 启动本地服务器

```bash
cd back
python main.py

# 看到以下输出表示成功：
# * Running on http://0.0.0.0:8080
```

### 4. 测试 API 端点

```bash
# 健康检查
curl http://localhost:8080/health

# 应返回:
# {"status": "ok", "timestamp": "..."}
```

---

## 📱 前端启动

### 1. 安装新依赖

```bash
cd "/Users/achilles/Documents/code/data science/front"
flutter pub get

# 应该看到:
# Resolving dependencies... (几秒钟)
# Got dependencies!
```

### 2. 验证依赖

```bash
flutter pub deps | grep intl

# 应该看到:
# intl 0.19.0
```

### 3. 运行前端

```bash
# Web 版本（推荐用于开发）
flutter run -d chrome

# 或 macOS 版本
flutter run -d macos
```

---

## 🧪 功能测试流程

### 测试 1: 分析文件并自动保存历史

1. **登录应用**
   - 使用 Google 登录或邮箱登录

2. **上传并分析文件**
   - 点击 "选择文件"
   - 选择一个 CSV 文件（例如 `test_data.csv`）
   - 点击 "开始分析"
   - 等待分析完成

3. **查看后端日志**
   - 在后端终端查看日志输出
   - 应该看到类似：

     ```
     [uid123] 分析记录已保存: abc123xyz
     ```

4. **验证 Firestore**
   - 打开 Firebase Console > Firestore Database
   - 导航到: `users/{your_uid}/history`
   - 应该看到新保存的记录

### 测试 2: 查看历史记录

1. **添加导航（临时）**
   - 在 `data_analysis_screen.dart` 的 AppBar 添加按钮：

   ```dart
   actions: [
     IconButton(
       icon: const Icon(Icons.history),
       onPressed: () {
         Navigator.push(
           context,
           MaterialPageRoute(builder: (_) => const HistoryScreen()),
         );
       },
     ),
     // 其他按钮...
   ],
   ```

2. **打开历史页面**
   - 点击历史图标按钮
   - 应该看到刚才分析的文件

3. **验证显示**
   - ✓ 文件名正确
   - ✓ 时间格式正确（yyyy-MM-dd HH:mm）
   - ✓ 质量分数显示
   - ✓ 颜色编码正确（绿/橙/红）

### 测试 3: 查看详情

1. **点击历史卡片**
   - 应该弹出对话框

2. **验证详情内容**
   - ✓ 文件名
   - ✓ 质量分数
   - ✓ 基本信息（行数/列数）
   - ✓ 数据质量指标（缺失率/异常值/重复行）

### 测试 4: 删除记录

1. **点击删除按钮**
   - 应该显示确认对话框

2. **确认删除**
   - 点击 "删除"
   - 记录从列表消失
   - 显示 "已删除" 提示

3. **验证 Firestore**
   - 刷新 Firestore Console
   - 记录应该已被删除

### 测试 5: 下拉刷新

1. **添加新记录**
   - 返回分析页面
   - 分析另一个文件

2. **刷新历史**
   - 返回历史页面
   - 下拉刷新
   - 新记录应该出现在列表顶部

---

## 🔍 故障排查

### 问题 1: Firestore 连接失败

**症状**: 后端日志显示 `Failed to get Firestore client`

**解决**:

```bash
# 1. 确认 Firebase Admin SDK 初始化成功
# 查看后端日志，应该看到：
# Firebase Admin SDK initialized successfully

# 2. 检查服务账号密钥
ls back/firebase-credentials.json
# 如果不存在，从 Firebase Console 下载

# 3. 设置环境变量（如果需要）
export GOOGLE_APPLICATION_CREDENTIALS="path/to/firebase-credentials.json"
```

### 问题 2: 历史记录为空

**症状**: 前端显示 "暂无历史记录"

**解决**:

```bash
# 1. 检查是否已分析过文件
# 2. 查看后端日志，确认保存成功
# 3. 检查 Firestore Console，确认数据存在
# 4. 查看浏览器控制台，检查 API 请求是否成功
# 5. 确认用户 UID 一致
```

### 问题 3: 时间显示错误

**症状**: 时间显示为 "未知时间"

**解决**:

```bash
# 1. 确认 intl 包已安装
flutter pub get

# 2. 检查时间戳格式
# 后端应返回 ISO 8601 格式：2024-01-01T12:00:00Z
```

### 问题 4: 删除失败

**症状**: 点击删除后显示错误

**解决**:

```bash
# 1. 检查 Firestore 安全规则
# 2. 确认用户已认证
# 3. 查看后端日志
# 4. 验证 record_id 正确
```

---

## 📊 验证清单

使用此清单验证所有功能：

### 后端

- [ ] `back/config.py` 配置正确
- [ ] `back/services/history_service.py` 文件存在
- [ ] `back/api/history.py` 文件存在
- [ ] `back/main.py` 注册了 `history_bp`
- [ ] `back/api/analysis.py` 调用了 `save_analysis_record`
- [ ] 后端启动无错误
- [ ] API 端点响应正常

### 前端

- [ ] `front/lib/services/api_service.dart` 添加了历史方法
- [ ] `front/lib/screens/history_screen.dart` 文件存在
- [ ] `front/pubspec.yaml` 包含 `intl` 依赖
- [ ] `flutter pub get` 成功
- [ ] 应用启动无错误
- [ ] 历史页面正常显示

### Firestore

- [ ] 数据库已启用
- [ ] 区域设置为 asia-northeast1
- [ ] 安全规则已配置
- [ ] 可以在控制台看到数据

### 功能测试

- [ ] 分析文件后自动保存历史
- [ ] 历史列表正常显示
- [ ] 时间格式正确
- [ ] 质量分数颜色正确
- [ ] 点击查看详情正常
- [ ] 删除功能正常
- [ ] 下拉刷新正常

---

## 🎯 下一步建议

### 1. 添加导航入口

在主应用中添加历史记录入口：

**方式 A**: AppBar 按钮

```dart
// data_analysis_screen.dart
AppBar(
  actions: [
    IconButton(
      icon: const Icon(Icons.history),
      onPressed: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const HistoryScreen()),
      ),
    ),
  ],
)
```

**方式 B**: 底部导航栏

```dart
BottomNavigationBar(
  items: [
    BottomNavigationBarItem(icon: Icon(Icons.analytics), label: '分析'),
    BottomNavigationBarItem(icon: Icon(Icons.history), label: '历史'),
  ],
)
```

**方式 C**: 抽屉菜单

```dart
Drawer(
  child: ListView(
    children: [
      ListTile(
        leading: Icon(Icons.analytics),
        title: Text('数据分析'),
        onTap: () { /* ... */ },
      ),
      ListTile(
        leading: Icon(Icons.history),
        title: Text('分析历史'),
        onTap: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const HistoryScreen()),
        ),
      ),
    ],
  ),
)
```

### 2. 优化功能

- 添加分页加载
- 实现搜索/筛选
- 支持导出历史记录
- 添加批量删除

### 3. 部署到生产环境

```bash
# 后端
cd back
gcloud app deploy

# 前端
cd front
flutter build web
firebase deploy --only hosting
```

---

## 📞 获取帮助

如果遇到问题：

1. **查看日志**
   - 后端：终端输出
   - 前端：浏览器控制台 (F12)

2. **检查文档**
   - `PHASE_3_COMPLETE.md` - 完整文档
   - `FULL_STACK_INTEGRATION_GUIDE.md` - 集成指南

3. **验证数据**
   - Firestore Console
   - API 响应

---

## ✅ 快速命令参考

```bash
# 启动后端
cd back && python main.py

# 安装前端依赖
cd front && flutter pub get

# 运行前端
cd front && flutter run -d chrome

# 部署后端
cd back && gcloud app deploy

# 部署前端
cd front && flutter build web && firebase deploy
```

---

**状态**: ✅ Phase 3 已完成  
**准备就绪**: 🚀 可以开始测试

祝测试顺利！🎉
