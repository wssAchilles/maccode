# 🚨 快速修复指南

## 问题总结

1. ✅ **Firestore 为空** → 正常！用户数据在 Firebase Authentication
2. ❌ **登录失败** → 邮箱不匹配（注册是 <123@gmail.com>，登录用了 <123@qq.com>）
3. ❌ **Google 登录失败** → redirect_uri_mismatch 配置错误

---

## 🎯 立即解决方案

### 问题1: 邮箱密码登录失败

**原因**：你输入的邮箱是 `123@qq.com`，但注册的是 `123@gmail.com`

**解决**（二选一）：

#### 方法A：使用正确的邮箱

```
邮箱：123@gmail.com  ← 使用这个
密码：你注册时设置的密码
```

#### 方法B：重新注册

1. 点击 **"立即注册"**
2. 输入：`123@qq.com`
3. 设置新密码（至少6位）
4. 点击 **"注册"**

---

### 问题2: Google 登录 redirect_uri_mismatch

**需要在 Google Cloud Console 配置重定向 URI**

#### 📝 详细步骤

1. **打开 Google Cloud Console**
   - 访问：<https://console.cloud.google.com/apis/credentials>
   - 选择项目：`data-science-44398`

2. **找到并编辑 OAuth 客户端**
   - 在 "OAuth 2.0 Client IDs" 列表中
   - 找到 ID 为 `355365849818-nre0eoukodlr0kvhs94utq2o5vlo1mk4`
   - 点击右侧的 **编辑图标** ✏️

3. **添加授权重定向 URI**

   在 **"已获授权的重定向 URI"** 部分，点击 **"添加 URI"**，添加：

   ```
   https://data-science-44398.web.app/__/auth/handler
   ```

   再点击 **"添加 URI"**，添加：

   ```
   https://data-science-44398.firebaseapp.com/__/auth/handler
   ```

   **重要提示**：
   - ✅ 必须是 `/__/auth/handler` 结尾
   - ✅ 使用 `https://`
   - ❌ 不能有尾部斜杠

4. **添加授权 JavaScript 来源**

   在 **"已获授权的 JavaScript 来源"** 部分，点击 **"添加 URI"**，添加：

   ```
   https://data-science-44398.web.app
   ```

   再点击 **"添加 URI"**，添加：

   ```
   https://data-science-44398.firebaseapp.com
   ```

5. **保存配置**
   - 点击底部的 **"保存"** 按钮
   - 等待 **5-10 分钟**让配置生效

6. **清除浏览器缓存**
   - Chrome: `Ctrl+Shift+Delete` (Mac: `Cmd+Shift+Delete`)
   - 选择：
     - ✓ Cookie 和其他网站数据
     - ✓ 缓存的图片和文件
   - 时间范围：**全部时间**
   - 点击 **"清除数据"**

7. **重新测试**
   - 访问：<https://data-science-44398.web.app>
   - 点击 **"使用 Google 登录"**
   - 应该可以正常登录了 ✅

---

## 📸 配置示例

### Google Cloud Console 应该看起来像这样

```
OAuth 2.0 客户端 ID

名称: Web client (auto created by Google Service)
客户端 ID: 355365849818-nre0eoukodlr0kvhs94utq2o5vlo1mk4.apps.googleusercontent.com

已获授权的 JavaScript 来源
  1. https://data-science-44398.web.app
  2. https://data-science-44398.firebaseapp.com
                                          [+ 添加 URI]

已获授权的重定向 URI
  1. https://data-science-44398.web.app/__/auth/handler
  2. https://data-science-44398.firebaseapp.com/__/auth/handler
                                          [+ 添加 URI]

                    [取消]  [保存]
```

---

## ✅ 数据存储说明

### 你的数据**已经正确存储**

**误解**：Firestore Database 应该有数据
**事实**：用户数据在 Firebase Authentication

```
Firebase Authentication (用户标签)
  └── 用户列表
       └── 123@gmail.com  ← 你的用户在这里 ✅
```

**Firestore Database 为空是正常的**，因为：

- ✅ 用户认证 → Firebase Authentication
- ✅ 数据分析 → GAE Backend（临时处理）
- ❌ Firestore → 本应用未使用

---

## 🧪 验证前后端是否打通

### 测试步骤

1. **登录**（使用正确的邮箱密码）
2. **选择 CSV 文件**
3. **点击 "开始分析"**
4. **等待结果**

#### ✅ 成功标志

- 看到加载动画
- 5-10秒后显示分析结果
- 结果包含：基本信息、统计数据、数据预览

#### ❌ 失败标志

- 401 错误 → Token 验证失败
- CORS 错误 → 后端未启动或配置错误
- 网络错误 → GAE 未部署

---

## 💡 推荐做法

### 现在立即可用的方法

**使用邮箱密码登录** - 无需任何配置！

1. 打开：<https://data-science-44398.web.app>
2. 使用正确的邮箱：`123@gmail.com`
3. 输入密码
4. 点击 **"登录"**
5. 开始使用数据分析功能 ✅

**优点**：

- ✅ 立即可用
- ✅ 不依赖 Google
- ✅ 功能完全相同

### Google 登录（可选）

按照上面的步骤配置 OAuth 后，可以使用 Google 一键登录。

---

## 📋 检查清单

### 邮箱密码登录

- [ ] 使用注册时的邮箱（<123@gmail.com>）
- [ ] 密码至少6位
- [ ] 点击"登录"按钮
- [ ] 看到用户信息显示

### Google 登录（需要配置）

- [ ] 已在 Google Cloud Console 添加重定向 URI
- [ ] 已添加 JavaScript 来源
- [ ] 已保存并等待5-10分钟
- [ ] 已清除浏览器缓存
- [ ] 重新测试

### 数据分析功能

- [ ] 成功登录
- [ ] 可以选择 CSV 文件
- [ ] 点击"开始分析"
- [ ] 看到分析结果

---

## 🎯 总结

1. **Firestore 为空** → ✅ 正常，用户在 Authentication
2. **登录失败** → ✅ 使用 <123@gmail.com> 登录
3. **Google 登录失败** → ⏳ 需要配置 redirect URI

**当前可用**：邮箱密码登录 + 完整数据分析功能

**需要配置**：Google 登录（可选，按上述步骤配置）

---

详细说明请查看：**[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**

*更新时间: 2025-11-18*
