#!/usr/bin/env python3
"""
手动训练模型并保存元数据到 Firestore
用于初始化或重新训练模型
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.ml_service import EnergyPredictor

def main():
    print("=" * 80)
    print("开始训练模型并保存元数据")
    print("=" * 80)
    
    try:
        # 创建预测器实例
        predictor = EnergyPredictor()
        
        # 训练模型（会自动保存到 Firebase Storage 和 Firestore）
        print("\n正在训练模型...")
        result = predictor.train_model(
            n_estimators=100,
            test_size=0.2,
            random_state=42,
            use_firebase_storage=True
        )
        
        print("\n" + "=" * 80)
        print("✅ 训练完成！")
        print("=" * 80)
        print(f"训练集 MAE: {result['train_mae']:.2f} kW")
        print(f"训练集 RMSE: {result['train_rmse']:.2f} kW")
        print(f"测试集 MAE: {result['test_mae']:.2f} kW")
        print(f"测试集 RMSE: {result['test_rmse']:.2f} kW")
        print("=" * 80)
        
        # 验证元数据是否保存成功
        print("\n正在验证 Firestore 元数据...")
        metadata = EnergyPredictor.get_model_metadata()
        
        if metadata:
            print("✅ Firestore 元数据验证成功！")
            print(f"   模型类型: {metadata.get('model_type')}")
            print(f"   模型版本: {metadata.get('model_version')}")
            print(f"   训练时间: {metadata.get('trained_at')}")
            print(f"   测试集 MAE: {metadata.get('metrics', {}).get('test_mae')} kW")
            print(f"   训练样本数: {metadata.get('training_samples')}")
            print(f"   数据来源: {metadata.get('data_source')}")
            print(f"   状态: {metadata.get('status')}")
        else:
            print("❌ Firestore 元数据未找到！")
            print("   请检查 Firestore 配置和权限")
        
        print("\n" + "=" * 80)
        print("完成！现在可以在前端查看模型信息了")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
