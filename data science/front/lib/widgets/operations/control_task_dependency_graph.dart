/// Lightweight dependency topology view for control tasks.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/control_task_record.dart';

class ControlTaskDependencyGraph extends StatelessWidget {
  const ControlTaskDependencyGraph({
    super.key,
    required this.taskId,
    required this.dependencies,
    this.dependencyDetails = const [],
    this.highlightedTaskId,
    this.onNodeTap,
  });

  final String taskId;
  final List<String> dependencies;
  final List<ControlTaskDependencyDetail> dependencyDetails;
  final String? highlightedTaskId;
  final ValueChanged<String>? onNodeTap;

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
                  accentColor: _dependencyAccentColor(
                    _lookupState(dependencies[index]),
                  ),
                  caption: _dependencyCaption(
                    _lookupState(dependencies[index]),
                  ),
                  highlighted: highlightedTaskId == dependencies[index],
                  onTap: onNodeTap == null
                      ? null
                      : () => onNodeTap!(dependencies[index]),
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
                highlighted: highlightedTaskId == taskId,
                onTap: onNodeTap == null ? null : () => onNodeTap!(taskId),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String? _lookupState(String dependencyId) {
    for (final detail in dependencyDetails) {
      if (detail.id == dependencyId) {
        return detail.state;
      }
    }
    return null;
  }
}

class _DependencyNode extends StatelessWidget {
  const _DependencyNode({
    required this.label,
    required this.accentColor,
    this.caption,
    this.highlighted = false,
    this.onTap,
  });

  final String label;
  final Color accentColor;
  final String? caption;
  final bool highlighted;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minWidth: 88),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: accentColor.withValues(alpha: highlighted ? 0.18 : 0.12),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: accentColor.withValues(alpha: highlighted ? 0.7 : 0.35),
            width: highlighted ? 1.4 : 1,
          ),
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
      ),
    );
  }
}

Color _dependencyAccentColor(String? state) {
  switch (state) {
    case 'missing':
      return AppColors.error;
    case 'paused':
      return AppColors.warning;
    default:
      return AppColors.info;
  }
}

String? _dependencyCaption(String? state) {
  switch (state) {
    case 'missing':
      return '缺失依赖';
    case 'paused':
      return '暂停依赖';
    case 'ready':
      return '依赖就绪';
    default:
      return null;
  }
}
