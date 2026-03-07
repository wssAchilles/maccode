/// 数据分析页状态组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

class DataAnalysisLoadingView extends StatelessWidget {
  const DataAnalysisLoadingView({super.key, required this.isAuthenticated});

  final bool isAuthenticated;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(
            isAuthenticated ? '分析中，请稍候...' : '登录中...',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          const Text('GAE 后端可能需要几秒钟唤醒', style: TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }
}

class DataAnalysisStartButton extends StatelessWidget {
  const DataAnalysisStartButton({
    super.key,
    required this.canAnalyze,
    required this.onStart,
  });

  final bool canAnalyze;
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: AppDecorations.animationFast,
      height: 56,
      decoration: BoxDecoration(
        gradient: canAnalyze ? AppColors.ctaGradient : null,
        color: canAnalyze ? null : AppColors.textMuted.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        boxShadow: canAnalyze ? AppDecorations.shadowMd : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          key: const ValueKey('analysis-start-button'),
          onTap: canAnalyze ? onStart : null,
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
          child: Center(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.auto_awesome_rounded,
                  color: canAnalyze ? Colors.white : AppColors.textMuted,
                ),
                const SizedBox(width: 12),
                Text(
                  '开始分析',
                  style: AppTextStyles.button.copyWith(
                    color: canAnalyze ? Colors.white : AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class DataAnalysisErrorBanner extends StatelessWidget {
  const DataAnalysisErrorBanner({
    super.key,
    required this.message,
    required this.onDismiss,
  });

  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.errorLight,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(AppDecorations.radiusSm),
            ),
            child: const Icon(
              Icons.error_outline_rounded,
              color: AppColors.error,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.error),
            ),
          ),
          IconButton(
            key: const ValueKey('analysis-error-dismiss'),
            icon: const Icon(Icons.close_rounded, size: 18),
            onPressed: onDismiss,
            style: IconButton.styleFrom(foregroundColor: AppColors.error),
          ),
        ],
      ),
    );
  }
}
