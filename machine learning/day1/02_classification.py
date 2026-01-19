"""
分类问题入门示例
使用逻辑回归进行二分类任务
"""

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 50)
print("分类问题示例 - 逻辑回归")
print("=" * 50)

# 1. 生成分类数据集
X, y = make_classification(
    n_samples=100,      # 样本数量
    n_features=2,       # 特征数量
    n_informative=2,    # 有信息的特征数
    n_redundant=0,      # 冗余特征数
    random_state=42
)

print(f"\n数据集信息:")
print(f"  样本数量: {X.shape[0]}")
print(f"  特征数量: {X.shape[1]}")
print(f"  类别分布: {np.bincount(y)}")

# 2. 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

print(f"\n数据划分:")
print(f"  训练集: {X_train.shape[0]} 个样本")
print(f"  测试集: {X_test.shape[0]} 个样本")

# 3. 创建并训练分类模型
clf = LogisticRegression(random_state=42)
clf.fit(X_train, y_train)

print(f"\n模型参数:")
print(f"  系数 (coefficients): {clf.coef_[0]}")
print(f"  截距 (intercept): {clf.intercept_[0]:.4f}")

# 4. 进行预测
y_pred = clf.predict(X_test)

# 5. 评估模型
accuracy = accuracy_score(y_test, y_pred)
print(f"\n模型性能:")
print(f"  准确率 (Accuracy): {accuracy:.4f}")

# 混淆矩阵
cm = confusion_matrix(y_test, y_pred)
print(f"\n混淆矩阵:")
print(cm)

# 详细分类报告
print(f"\n分类报告:")
print(classification_report(y_test, y_pred, 
      target_names=['类别 0', '类别 1']))

# 6. 获取预测概率
y_pred_proba = clf.predict_proba(X_test)
print(f"\n预测概率示例（前5个样本）:")
for i in range(min(5, len(y_pred_proba))):
    print(f"  样本 {i}: 类别0概率={y_pred_proba[i][0]:.4f}, " +
          f"类别1概率={y_pred_proba[i][1]:.4f} -> 预测为{y_pred[i]}")

# 7. 可视化决策边界
plt.figure(figsize=(10, 6))

# 绘制训练数据
scatter = plt.scatter(X[:, 0], X[:, 1], c=y, cmap='viridis', 
                     s=100, alpha=0.6, edgecolors='k')

# 绘制决策边界
xx, yy = np.meshgrid(
    np.linspace(X[:, 0].min() - 1, X[:, 0].max() + 1, 200),
    np.linspace(X[:, 1].min() - 1, X[:, 1].max() + 1, 200)
)
Z = clf.predict(np.c_[xx.ravel(), yy.ravel()])
Z = Z.reshape(xx.shape)

plt.contourf(xx, yy, Z, alpha=0.3, cmap='viridis')
plt.contour(xx, yy, Z, colors='black', linewidths=0.5)

plt.xlabel('特征 1', fontsize=12)
plt.ylabel('特征 2', fontsize=12)
plt.title('逻辑回归 - 决策边界', fontsize=14, fontweight='bold')
plt.colorbar(scatter, label='类别')
plt.grid(True, alpha=0.3)
plt.savefig('classification.png', dpi=150, bbox_inches='tight')
plt.show()

print("\n图表已保存为 classification.png")
