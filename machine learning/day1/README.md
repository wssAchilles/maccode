# Day 1 - 机器学习入门

欢迎来到机器学习之旅！本文件夹包含了4个入门示例，帮助你理解机器学习的核心概念。

## 📚 课程内容

### 1. 线性回归 (`01_linear_regression.py`)

**学习目标：** 理解最基础的监督学习算法

**主要概念：**

- 什么是线性回归
- 特征（X）和标签（y）的关系
- 模型参数（斜率和截距）
- 评估指标（MSE、RMSE、R²）
- 预测新数据

**核心代码：**

```python
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X_train, y_train)  # 训练
predictions = model.predict(X_test)  # 预测
```

**你会学到：**

- ✅ 如何创建和训练模型
- ✅ 如何评估模型性能
- ✅ 如何进行预测
- ✅ 如何可视化结果

---

### 2. 分类问题 (`02_classification.py`)

**学习目标：** 理解分类任务和模型评估

**主要概念：**

- 什么是分类问题
- 逻辑回归算法
- 训练集/测试集划分
- 混淆矩阵
- 决策边界

**核心代码：**

```python
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
clf = LogisticRegression()
clf.fit(X_train, y_train)
accuracy = clf.score(X_test, y_test)
```

**你会学到：**

- ✅ 数据的训练/测试分割
- ✅ 分类模型的基本原理
- ✅ 如何评估分类模型（准确率、混淆矩阵）
- ✅ 决策边界的概念

---

### 3. 数据预处理 (`03_data_preprocessing.py`)

**学习目标：** 掌握数据准备的技巧

**主要概念：**

- 处理缺失值
- 特征标准化（Standardization）
- 特征归一化（Normalization）
- 离群值检测
- 特征相关性分析

**核心代码：**

```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer

# 处理缺失值
imputer = SimpleImputer(strategy='mean')
X_filled = imputer.fit_transform(X)

# 标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
```

**你会学到：**

- ✅ 为什么要预处理数据
- ✅ 不同的预处理方法及其用途
- ✅ 如何检测和处理异常值
- ✅ 特征缩放对模型的影响

---

### 4. 模型评估 (`04_model_evaluation.py`)

**学习目标：** 学会科学地评估模型性能

**主要概念：**

- 多个评估指标（准确率、精确率、召回率、F1分数）
- 交叉验证
- 学习曲线
- ROC曲线和AUC
- 特征重要性

**核心代码：**

```python
from sklearn.model_selection import cross_val_score, learning_curve
from sklearn.metrics import accuracy_score, precision_score, recall_score

# 交叉验证
scores = cross_val_score(model, X, y, cv=5)

# 学习曲线
learning_curve(model, X, y, cv=5)
```

**你会学到：**

- ✅ 不同指标的含义和用途
- ✅ 如何使用交叉验证
- ✅ 从学习曲线识别过拟合/欠拟合
- ✅ 如何解读ROC曲线

---

## 🚀 快速开始

### 前置要求

```bash
pip install scikit-learn numpy pandas matplotlib
```

### 运行示例

```bash
# 运行线性回归示例


# 运行分类示例
python 02_classification.py

# 运行数据预处理示例
python 03_data_preprocessing.py

# 运行模型评估示例
python 04_model_evaluation.py
```

---

## 📊 学习路径建议

1. **首先运行** `01_linear_regression.py`

   - 理解最基础的模型
   - 学会读取代码输出
2. **然后运行** `03_data_preprocessing.py`

   - 理解数据的重要性
   - 学会数据处理技巧
3. **接着运行** `02_classification.py`

   - 理解分类问题
   - 学会处理真实数据
4. **最后运行** `04_model_evaluation.py`

   - 学会科学评估模型
   - 理解各种评估指标

---

## 💡 关键概念总结

| 概念             | 说明                                       |
| ---------------- | ------------------------------------------ |
| **特征**   | 用来预测的输入变量（X）                    |
| **标签**   | 我们要预测的目标变量（y）                  |
| **模型**   | 从特征到标签的数学映射                     |
| **训练**   | 从数据中学习模型参数的过程                 |
| **预测**   | 使用训练好的模型对新数据做出预测           |
| **评估**   | 衡量模型性能的过程                         |
| **过拟合** | 模型在训练数据上表现好，但在新数据上表现差 |
| **欠拟合** | 模型在训练数据和新数据上都表现差           |

---

## 🎯 常见问题

**Q: 为什么需要分割训练集和测试集？**
A: 防止过拟合。训练集用来训练模型，测试集用来评估模型在新数据上的真实表现。

**Q: 什么时候该标准化数据？**
A: 当特征的量纲（单位）差异很大时需要标准化。这样可以加快模型训练速度，提高准确性。

**Q: 应该使用哪个评估指标？**
A: 取决于你的具体问题。对于分类问题，准确率、精确率、召回率和F1分数都很重要。对于回归问题，MAE、MSE、RMSE是常用指标。

**Q: 学习曲线告诉我什么？**
A:

- 两条线都在低位且平行 → 欠拟合，需要更复杂的模型或更多特征
- 训练曲线高，测试曲线低 → 过拟合，需要更多数据或正则化
- 两条线都在高位且接近 → 理想状态

---

## 📖 推荐进阶学习

学完这些基础后，你可以探索：

- 🔹 决策树和随机森林
- 🔹 支持向量机（SVM）
- 🔹 K-均值聚类（无监督学习）
- 🔹 神经网络和深度学习
- 🔹 特征工程和模型优化

---

## 📝 笔记区域

在这里记下你的学习笔记...

---

**祝你学习愉快！加油！** 🎉
