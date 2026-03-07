/// 深度学习页面训练日志终端组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/animated_glass_card.dart';

class DeepLearningTerminalPanel extends StatelessWidget {
  const DeepLearningTerminalPanel({
    super.key,
    required this.isTraining,
    required this.logs,
  });

  final bool isTraining;
  final String logs;

  @override
  Widget build(BuildContext context) {
    return AnimatedGlassCard(
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.05),
              border: const Border(
                bottom: BorderSide(color: AppColors.glassBorder),
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.terminal_rounded,
                  size: 20,
                  color: AppColors.textSecondary,
                ),
                const SizedBox(width: 8),
                Text('Real-time Logs', style: AppTextStyles.labelLarge),
                const Spacer(),
                if (isTraining)
                  const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
          ),
          Container(
            key: const ValueKey('deep-learning-terminal'),
            height: 400,
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            color: const Color(0xFF1E293B),
            child: SingleChildScrollView(
              reverse: true,
              child: Text(
                logs.isEmpty ? 'Ready to train...' : logs,
                style: AppTextStyles.codeFont.copyWith(
                  color: const Color(0xFF34D399),
                  fontSize: 13,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
