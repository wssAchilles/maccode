/// Pro 功能入口组件 - 从 DataAnalysisScreen 提取
/// 【性能优化】使用 const 构造函数减少重建
library;

import 'package:flutter/material.dart';
import '../../config/app_theme.dart';
import '../common/animated_glass_card.dart';
import '../../screens/deep_learning_screen.dart';
import '../../screens/rag_screen.dart';

/// Pro 功能入口组件
class ProFeaturesSection extends StatelessWidget {
  const ProFeaturesSection({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 标题
        Row(
          children: [
            const Icon(Icons.rocket_launch_rounded, color: AppColors.primary, size: 20),
            const SizedBox(width: 8),
            Text('Advanced Intelligence (Cloud Run)', style: AppTextStyles.h4),
          ],
        ),
        const SizedBox(height: 16),
        // 功能卡片
        Row(
          children: [
            Expanded(child: _DeepLearningCard()),
            const SizedBox(width: 16),
            Expanded(child: _RagCard()),
          ],
        ),
      ],
    );
  }
}

/// Deep Learning 功能卡片
class _DeepLearningCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return AnimatedGlassCard(
      gradientBorder: AppColors.deepLearningGradient,
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => const DeepLearningScreen()),
        );
      },
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              gradient: AppColors.deepLearningGradient,
              borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
            ),
            child: const Icon(Icons.psychology_rounded, color: Colors.white, size: 28),
          ),
          const SizedBox(height: 12),
          Text('Deep Learning', style: AppTextStyles.labelLarge),
          const SizedBox(height: 4),
          Text('LSTM/GRU Time Series', style: AppTextStyles.labelSmall),
        ],
      ),
    );
  }
}

/// RAG 功能卡片
class _RagCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return AnimatedGlassCard(
      gradientBorder: AppColors.ragGradient,
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => const RagScreen()),
        );
      },
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              gradient: AppColors.ragGradient,
              borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
            ),
            child: const Icon(Icons.auto_stories_rounded, color: Colors.white, size: 28),
          ),
          const SizedBox(height: 12),
          Text('RAG Knowledge', style: AppTextStyles.labelLarge),
          const SizedBox(height: 4),
          Text('Interactive Q&A', style: AppTextStyles.labelSmall),
        ],
      ),
    );
  }
}
