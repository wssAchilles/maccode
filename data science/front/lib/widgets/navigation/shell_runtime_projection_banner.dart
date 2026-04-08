library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/main_shell_projection.dart';

class ShellRuntimeProjectionBanner extends StatelessWidget {
  const ShellRuntimeProjectionBanner({
    super.key,
    required this.projection,
  });

  final MainShellProjection projection;

  @override
  Widget build(BuildContext context) {
    final focusAlert = projection.focusAlert;
    final nextTask = projection.nextControlTask;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              _StatusChip(
                label: '当前工作台 · ${projection.activeTabLabel}',
                foreground: AppColors.primary,
                background: AppColors.primaryLight,
              ),
              _StatusChip(
                label: projection.hasPendingApprovals
                    ? '待审批 ${projection.pendingApprovalCount}'
                    : '审批队列空闲',
                foreground: projection.hasPendingApprovals
                    ? AppColors.warning
                    : AppColors.success,
                background: projection.hasPendingApprovals
                    ? const Color(0xFFFFF4E5)
                    : AppColors.successLight,
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            projection.selectedOperationLabel,
            style: AppTextStyles.labelLarge,
          ),
          const SizedBox(height: 6),
          Text(
            nextTask == null
                ? '规划任务已进入稳定态，当前没有需要立即介入的计划项。'
                : '下一关注任务 · ${projection.nextControlTaskLabel}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (focusAlert != null) ...[
            const SizedBox(height: 10),
            Text(
              '${focusAlert.title} · ${focusAlert.message}',
              style: AppTextStyles.bodySmall.copyWith(
                color: _alertTone(focusAlert.severity),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Color _alertTone(String severity) {
    switch (severity) {
      case 'critical':
      case 'error':
        return AppColors.error;
      case 'warning':
        return AppColors.warning;
      case 'success':
        return AppColors.success;
      default:
        return AppColors.textSecondary;
    }
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.foreground,
    required this.background,
  });

  final String label;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelMedium.copyWith(
          color: foreground,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
