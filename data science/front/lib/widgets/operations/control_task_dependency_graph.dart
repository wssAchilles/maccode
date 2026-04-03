/// Lightweight dependency topology view for control tasks.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';

class ControlTaskDependencyGraph extends StatelessWidget {
  const ControlTaskDependencyGraph({
    super.key,
    required this.taskId,
    required this.dependencies,
  });

  final String taskId;
  final List<String> dependencies;

  @override
  Widget build(BuildContext context) {
    if (dependencies.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('依赖拓扑', style: AppTextStyles.labelMedium),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              for (var index = 0; index < dependencies.length; index++) ...[
                _DependencyNode(
                  label: dependencies[index],
                  accentColor: AppColors.info,
                ),
                const Icon(
                  Icons.arrow_forward_rounded,
                  size: 18,
                  color: AppColors.textSecondary,
                ),
              ],
              _DependencyNode(
                label: taskId,
                accentColor: AppColors.primary,
                caption: '当前任务',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DependencyNode extends StatelessWidget {
  const _DependencyNode({
    required this.label,
    required this.accentColor,
    this.caption,
  });

  final String label;
  final Color accentColor;
  final String? caption;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 88),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: accentColor.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: accentColor.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (caption != null) ...[
            Text(
              caption!,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 2),
          ],
          Text(label, style: AppTextStyles.labelMedium),
        ],
      ),
    );
  }
}
