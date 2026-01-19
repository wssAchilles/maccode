"""
模型评估方法入门示例
展示交叉验证、学习曲线等评估技巧
"""

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_iris
from sklearn.model_selection import (
    cross_val_score, 
    learning_curve, 
    KFold, 
    train_test_split
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, 
    precision_score, 
    recall_score, 
    f1_score,
    roc_auc_score,
    roc_curve,
    auc
)

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 50)
print("模型评估示例")
print("=" * 50)

# 1. 加载数据集
iris = load_iris()
X, y = iris.data, iris.target

# 转换为二分类问题（便于演示ROC曲线）
y_binary = (y == 0).astype(int)

print(f"\n数据集信息:")
print(f"  样本数: {X.shape[0]}")
print(f"  特征数: {X.shape[1]}")
print(f"  类别数: {len(np.unique(y_binary))}")

# 2. 划分数据集
X_train, X_test, y_train, y_test = train_test_split(
    X, y_binary, test_size=0.3, random_state=42
)

# 3. 训练模型
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)
y_pred = clf.predict(X_test)
y_pred_proba = clf.predict_proba(X_test)[:, 1]

# 4. 多种评估指标
print("\n4. 评估指标:")
print(f"  准确率 (Accuracy): {accuracy_score(y_test, y_pred):.4f}")
print(f"  精确率 (Precision): {precision_score(y_test, y_pred):.4f}")
print(f"  召回率 (Recall): {recall_score(y_test, y_pred):.4f}")
print(f"  F1分数 (F1-Score): {f1_score(y_test, y_pred):.4f}")
print(f"  ROC-AUC: {roc_auc_score(y_test, y_pred_proba):.4f}")

# 5. 交叉验证
print("\n5. 交叉验证 (5-折):")
cv_scores = cross_val_score(clf, X, y_binary, cv=5, scoring='accuracy')
print(f"  各折精度: {cv_scores}")
print(f"  平均精度: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

# 6. 绘制学习曲线
print("\n6. 生成学习曲线...")

train_sizes, train_scores, val_scores = learning_curve(
    RandomForestClassifier(n_estimators=50, random_state=42),
    X, y_binary,
    cv=5,
    train_sizes=np.linspace(0.1, 1.0, 10),
    scoring='accuracy',
    n_jobs=-1
)

train_mean = np.mean(train_scores, axis=1)
train_std = np.std(train_scores, axis=1)
val_mean = np.mean(val_scores, axis=1)
val_std = np.std(val_scores, axis=1)

# 7. 绘制ROC曲线
fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
roc_auc = auc(fpr, tpr)

# 8. 创建可视化图表
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 学习曲线
axes[0].plot(train_sizes, train_mean, 'o-', color='r', label='训练集')
axes[0].fill_between(train_sizes, train_mean - train_std, 
                      train_mean + train_std, alpha=0.2, color='r')
axes[0].plot(train_sizes, val_mean, 'o-', color='g', label='验证集')
axes[0].fill_between(train_sizes, val_mean - val_std, 
                      val_mean + val_std, alpha=0.2, color='g')
axes[0].set_xlabel('训练集大小', fontsize=11)
axes[0].set_ylabel('准确率', fontsize=11)
axes[0].set_title('学习曲线', fontsize=12, fontweight='bold')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# ROC曲线
axes[1].plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC (AUC = {roc_auc:.3f})')
axes[1].plot([0, 1], [0, 1], 'k--', linewidth=1, label='随机分类器')
axes[1].set_xlabel('假正例率 (FPR)', fontsize=11)
axes[1].set_ylabel('真正例率 (TPR)', fontsize=11)
axes[1].set_title('ROC 曲线', fontsize=12, fontweight='bold')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('model_evaluation.png', dpi=150, bbox_inches='tight')
plt.show()

print("\n图表已保存为 model_evaluation.png")

# 9. 特征重要性
print("\n9. 特征重要性:")
feature_importance = clf.feature_importances_
for name, importance in zip(iris.feature_names, feature_importance):
    print(f"  {name}: {importance:.4f}")
