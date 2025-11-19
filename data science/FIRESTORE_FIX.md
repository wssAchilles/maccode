# Firestore 配置修复说明

## 问题诊断

### 原始错误
```
The Cloud Firestore API is not available for Firestore in Datastore Mode
```

### 根本原因
Firebase 项目 `data-science-44398` 有两个数据库：
1. `(default)` - **Datastore Mode** (默认，但不支持 Firestore API)
2. `my-datasci-project-bucket` - **Firestore Native Mode** (支持完整 Firestore API)

代码原本使用默认数据库，导致 API 调用失败。

## 解决方案

### 修改内容
**文件**: `back/services/history_service.py`

```python
# 修改前
return firestore.client()

# 修改后
return firestore.client(database_id='my-datasci-project-bucket')
```

### 数据库对比

| 特性 | Datastore Mode | Firestore Native Mode |
|------|----------------|----------------------|
| 用途 | App Engine 传统应用 | 现代应用，实时同步 |
| API | Datastore API | Firestore API |
| 实时更新 | ❌ 不支持 | ✅ 支持 |
| 客户端 SDK | ❌ 有限 | ✅ 完整支持 |
| 查询能力 | 基础 | 高级（复合查询） |

## 数据结构

### Firestore 集合结构
```
users/
  └── {uid}/
      └── history/
          └── {record_id}/
              ├── filename: string
              ├── storage_url: string
              ├── created_at: timestamp
              ├── analysis_summary: object
              │   ├── basic_info
              │   ├── quality_analysis
              │   ├── correlation_analysis
              │   └── statistical_tests
              └── metadata: object
```

### 示例文档
```json
{
  "filename": "orders.csv",
  "storage_url": "gs://bucket/path/to/file.csv",
  "created_at": "2025-11-19T15:28:49Z",
  "analysis_summary": {
    "basic_info": {
      "rows": 1000,
      "columns": 10,
      "memory_usage": "78.2 KB"
    },
    "quality_analysis": {
      "quality_score": 97.3,
      "quality_metrics": {
        "missing_rate": 0.5,
        "total_outliers": 12,
        "duplicate_rows": 0
      }
    }
  }
}
```

## 验证步骤

### 1. 检查数据库列表
```bash
gcloud firestore databases list --project=data-science-44398
```

### 2. 查看 Firestore 数据
访问 Firebase Console:
https://console.firebase.google.com/project/data-science-44398/firestore/databases/my-datasci-project-bucket/data

### 3. 测试保存功能
1. 登录前端应用
2. 上传并分析 CSV 文件
3. 检查 Firestore 是否有新记录
4. 点击"历史记录"按钮查看列表

### 4. 查看后端日志
```bash
gcloud app logs read --limit 20 --service default | grep history
```

成功日志应显示：
```
✅ Analysis record saved successfully: {record_id}
```

## 前端历史记录功能

### 新增按钮位置
- **位置**: AppBar 右侧，登出按钮左边
- **图标**: `Icons.history`
- **功能**: 导航到 `HistoryScreen`

### HistoryScreen 功能
- ✅ 显示分析历史列表
- ✅ 按时间倒序排列
- ✅ 显示质量评分（颜色编码）
- ✅ 查看详细信息
- ✅ 删除记录
- ✅ 刷新列表
- ✅ 空状态提示

## API 端点

### 获取历史列表
```
GET /api/history?limit=20
Authorization: Bearer {firebase_token}
```

### 获取详细记录
```
GET /api/history/{record_id}
Authorization: Bearer {firebase_token}
```

### 删除记录
```
DELETE /api/history/{record_id}
Authorization: Bearer {firebase_token}
```

## 部署清单

- [x] 修改 `history_service.py` 使用正确的数据库
- [x] 添加历史记录按钮到前端 AppBar
- [x] 修复 `history_screen.dart` 语法错误
- [x] 重新部署后端到 GAE
- [x] 重新部署前端到 Firebase Hosting

## 预期结果

1. **后端**: 分析完成后自动保存记录到 Firestore
2. **前端**: 
   - 登录后显示历史记录按钮
   - 点击按钮查看历史列表
   - 可以查看详情和删除记录
3. **Firestore**: 
   - 在 `my-datasci-project-bucket` 数据库中
   - 路径: `users/{uid}/history/{record_id}`
   - 实时同步更新

## 故障排查

### 问题: Firestore 仍然为空
**检查**:
1. 确认使用正确的数据库 ID
2. 检查后端日志是否有错误
3. 验证 Firebase Admin SDK 权限

### 问题: 前端没有历史按钮
**检查**:
1. 确认前端已重新构建和部署
2. 清除浏览器缓存
3. 检查是否已登录

### 问题: 权限错误
**检查**:
1. Firestore 规则是否正确配置
2. Firebase ID Token 是否有效
3. 用户是否已认证

## 相关文档

- [Firestore Native Mode vs Datastore Mode](https://cloud.google.com/datastore/docs/firestore-or-datastore)
- [Firebase Admin SDK - Firestore](https://firebase.google.com/docs/firestore/server/start)
- [Phase 3 完整文档](./PHASE_3_COMPLETE.md)
