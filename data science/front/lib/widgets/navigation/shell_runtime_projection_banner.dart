library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/main_shell_projection.dart';

class ShellRuntimeProjectionBanner extends StatelessWidget {
  const ShellRuntimeProjectionBanner({super.key, required this.projection});

  final MainShellProjection projection;

  @override
  Widget build(BuildContext context) {
    final focusAlert = projection.focusAlert;
    final nextTask = projection.nextControlTask;
    final operationSession = projection.operationSession;

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
              _StatusChip(
                label: operationSession.statusLabel,
                foreground: operationSession.hasSelection
                    ? AppColors.primary
                    : AppColors.textSecondary,
                background: operationSession.hasSelection
                    ? AppColors.primaryLight
                    : AppColors.surface,
              ),
              if (projection.unreadNotificationCount > 0)
                _StatusChip(
                  label: '未读通知 ${projection.unreadNotificationCount}',
                  foreground: AppColors.warning,
                  background: const Color(0xFFFFF4E5),
                ),
              _StatusChip(
                label: projection.isDegraded
                    ? '共享快照降级 ${projection.degradedSections.length}'
                    : '共享快照 ${_snapshotLabel(projection.snapshotGeneratedAt)}',
                foreground: projection.isDegraded
                    ? AppColors.warning
                    : AppColors.success,
                background: projection.isDegraded
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
          if (projection.hasActiveAction) ...[
            const SizedBox(height: 6),
            Text(
              '控制动作 · ${projection.activeActionLabel}',
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.primary),
            ),
          ],
          if ((operationSession.latestMessage ?? '').trim().isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              operationSession.latestMessage!,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
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

  String _snapshotLabel(DateTime? value) {
    if (value == null) {
      return '就绪';
    }
    final local = value.toLocal();
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
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
