/// 数据分析页状态组件
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class DataAnalysisLoadingView extends StatelessWidget {
  const DataAnalysisLoadingView({super.key, required this.isAuthenticated});

  final bool isAuthenticated;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: GlassCard(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(
              isAuthenticated ? '分析任务执行中' : '认证处理中',
              style: AppTextStyles.h4,
            ),
            const SizedBox(height: 8),
            Text(
              isAuthenticated ? '正在上传数据、唤醒分析服务并生成结果面板。' : '正在建立会话并准备访问分析能力。',
              textAlign: TextAlign.center,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'GAE 后端可能需要几秒钟冷启动。',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class DataAnalysisStartButton extends StatelessWidget {
  const DataAnalysisStartButton({
    super.key,
    required this.canAnalyze,
    required this.onStart,
    this.disabledReason,
  });

  final bool canAnalyze;
  final VoidCallback onStart;
  final String? disabledReason;

  @override
  Widget build(BuildContext context) {
    final button = AnimatedContainer(
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
    final reason = disabledReason;
    if (canAnalyze || reason == null || reason.isEmpty) {
      return button;
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Tooltip(message: reason, child: button),
        const SizedBox(height: 8),
        Text(
          reason,
          textAlign: TextAlign.center,
          style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted),
        ),
      ],
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
