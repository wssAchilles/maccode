# 🔧 Google People API 启用指南

## 问题描述

Google 登录弹出窗口正常，但登录后出现红色错误：

```
People API has not been used in project 355365849818 before or it is disabled
```

## 原因

`google_sign_in` 插件需要使用 **Google People API** 来获取用户信息（姓名、邮箱、头像），但该 API 默认未启用。

---

## ✅ 解决方案

### 方法1：直接启用（推荐）

#### 步骤1：访问 API 启用页面

点击或访问这个链接：

```
https://console.developers.google.com/apis/api/people.googleapis.com/overview?project=355365849818
```

#### 步骤2：点击启用

在页面中央会看到一个蓝色的 **"启用"** 按钮，点击它。

#### 步骤3：等待确认

看到 "API 已启用" 的提示后，People API 就成功启用了。

---

### 方法2：手动搜索启用

#### 步骤1：打开 Google Cloud Console

访问：<https://console.cloud.google.com/>

#### 步骤2：选择项目

确保选择了正确的项目：`data-science-44398`

#### 步骤3：打开 API 库

- 点击左上角 **☰ 菜单**
- 选择 **APIs & Services** → **Library**

#### 步骤4：搜索 People API

- 在搜索框输入：`People API`
- 点击搜索结果中的 **"Google People API"**

#### 步骤5：启用 API

- 点击页面中央的 **"启用"** 按钮
- 等待几秒钟，直到看到 "API 已启用"

---

## 🧪 测试步骤

### 1. 清除缓存（可选）

如果启用后还是报错，清除浏览器缓存：

- Chrome: `Ctrl+Shift+Delete` (Mac: `Cmd+Shift+Delete`)
- 选择：Cookie 和缓存
- 时间范围：过去 1 小时

### 2. 重新测试

1. 访问：<https://data-science-44398.web.app>
2. 点击 **"使用 Google 登录"**
3. 选择 Google 账号
4. 应该看到：**"欢迎, [你的名字]!"** ✅

---

## 📋 需要启用的 API 列表

对于完整的 Google 登录功能，确保以下 API 已启用：

### 必需的 API

- ✅ **Google People API** - 获取用户信息
- ✅ **Google Identity Toolkit API** - Firebase Auth（通常已启用）

### 可选的 API（本项目未使用）

- Google Drive API - 如需访问用户 Drive
- Google Calendar API - 如需访问日历
- Gmail API - 如需访问邮件

---

## 🔍 如何检查 API 是否已启用

### 方法1：访问 API 列表

1. 打开：<https://console.cloud.google.com/apis/dashboard>
2. 选择项目：`data-science-44398`
3. 查看 **"已启用的 API 和服务"** 列表
4. 应该看到 **"Google People API"** 在列表中

### 方法2：查看指标

1. 打开：<https://console.cloud.google.com/apis/api/people.googleapis.com/metrics?project=355365849818>
2. 如果可以看到指标页面，说明 API 已启用
3. 如果显示 "API 未启用"，点击启用按钮

---

## ⚠️ 常见问题

### Q1: 启用后还是报同样的错误？

**A**:

1. 等待 1-2 分钟让配置生效
2. 清除浏览器缓存
3. 刷新页面重新登录

### Q2: 找不到 "启用" 按钮？

**A**:

- 可能 API 已经启用了
- 检查页面是否显示 "管理" 或 "停用" 按钮
- 如果是，说明 API 已启用

### Q3: 启用后显示配额不足？

**A**:

- People API 免费配额：每天 20,000 次请求
- 对于个人项目，免费配额完全够用
- 如果超出，需要启用计费

### Q4: 是否需要创建凭据？

**A**:

- ❌ 不需要！OAuth 客户端 ID 已经配置
- ✅ 只需启用 API 即可

---

## 🎯 完整的 Google 登录配置清单

### Google Cloud Console

- [x] 创建 OAuth 2.0 客户端 ID
- [x] 配置授权重定向 URI
- [x] 配置授权 JavaScript 来源
- [x] 启用 People API ← **新增！**

### Firebase Console

- [x] 启用 Google 登录方式
- [x] 配置 Web SDK

### 前端代码

- [x] 添加 `google_sign_in` 依赖
- [x] 配置 Web 客户端 ID
- [x] 实现登录逻辑

---

## 📊 People API 用途说明

`google_sign_in` 插件使用 People API 获取以下信息：

```json
{
  "displayName": "张三",
  "email": "user@gmail.com",
  "photoUrl": "https://lh3.googleusercontent.com/...",
  "id": "1234567890"
}
```

这些信息会显示在你的应用中：

```
✓ 张三 (user@gmail.com)
```

---

## 🚀 预期效果

### 启用 People API 前

```
点击 Google 登录
  ↓
弹出 Google 登录窗口
  ↓
选择账号并授权
  ↓
❌ 红色错误：People API has not been used
```

### 启用 People API 后

```
点击 Google 登录
  ↓
弹出 Google 登录窗口
  ↓
选择账号并授权
  ↓
✅ 登录成功："欢迎, 张三!"
  ↓
可以使用数据分析功能
```

---

## 💰 费用说明

### People API 配额

**免费额度**：

- 每天 20,000 次请求
- 每 100 秒 600 次请求
- 每个用户每 100 秒 60 次请求

**实际使用**：

- 每次 Google 登录：1-2 次请求
- 个人项目：完全免费

**计费**（超出免费额度后）：

- 每 1,000 次请求：$0.001
- 对于小型项目，几乎不会产生费用

---

## ✅ 总结

1. **问题**：Google 登录后报错 People API 未启用
2. **原因**：GCP 项目中未启用 People API
3. **解决**：访问 <https://console.developers.google.com/apis/api/people.googleapis.com/overview?project=355365849818> 并点击"启用"
4. **结果**：Google 登录完全可用 ✅

---

*更新时间: 2025-11-18*
*适用版本: v1.0.0*
