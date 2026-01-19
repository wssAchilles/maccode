"""
线性回归入门示例
展示如何使用scikit-learn进行简单的线性回归
"""

import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

# 设置中文字体（可选）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 1. 创建样本数据
# 生成一组有线性关系的数据：y ≈ 2x + 1 + 噪声
np.random.seed(42)
X = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]).reshape(-1, 1)  # 特征（输入）
y = 2 * X.flatten() + 1 + np.random.normal(0, 2, 10)  # 标签（输出）

print("=" * 50)
print("线性回归示例")
print("=" * 50)
print(f"\n输入特征 X:\n{X.flatten()}")
print(f"\n输出标签 y:\n{y}")

# 2. 创建并训练模型
model = LinearRegression()
model.fit(X, y)

print(f"\n模型参数:")
print(f"  斜率 (slope): {model.coef_[0]:.4f}")
print(f"  截距 (intercept): {model.intercept_:.4f}")

# 3. 预测
y_pred = model.predict(X)

# 4. 评估模型
mse = mean_squared_error(y, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y, y_pred)

print(f"\n模型评估指标:")
print(f"  均方误差 (MSE): {mse:.4f}")
print(f"  均方根误差 (RMSE): {rmse:.4f}")
print(f"  决定系数 (R²): {r2:.4f}")

# 5. 预测新数据
new_data = np.array([[11], [12]])
predictions = model.predict(new_data)
print(f"\n新数据预测:")
for i, pred in enumerate(predictions):
    print(f"  当 X={new_data[i][0]} 时，预测 y≈{pred:.2f}")

# 6. 可视化
plt.figure(figsize=(10, 6))
plt.scatter(X, y, color='blue', label='真实数据', s=100, alpha=0.6)
plt.plot(X, y_pred, color='red', linewidth=2, label='回归直线')
plt.xlabel('特征 X', fontsize=12)
plt.ylabel('目标 y', fontsize=12)
plt.title('线性回归示例', fontsize=14, fontweight='bold')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('linear_regression.png', dpi=150, bbox_inches='tight')
plt.show()

print("\n图表已保存为 linear_regression.png")
