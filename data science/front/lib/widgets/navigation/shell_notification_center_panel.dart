library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/shell_action_outcome.dart';
import '../../models/shell_runtime_notification.dart';
import '../../models/workbench_runtime_models.dart';
import '../common/glass_card.dart';

class ShellNotificationCenterPanel extends StatelessWidget {
  const ShellNotificationCenterPanel({
    super.key,
    required this.notifications,
    required this.onMarkAllRead,
    required this.onMarkRead,
    required this.onDismiss,
    required this.onOpenOperation,
  });

  final List<ShellRuntimeNotification> notifications;
  final VoidCallback onMarkAllRead;
  final ValueChanged<String> onMarkRead;
  final ValueChanged<String> onDismiss;
  final ValueChanged<String> onOpenOperation;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text('全局通知中心', style: AppTextStyles.labelLarge)),
            if (notifications.isNotEmpty)
              TextButton.icon(
                onPressed: onMarkAllRead,
                icon: const Icon(Icons.done_all_rounded),
                label: const Text('全部已读'),
              ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          '收口控制动作反馈、运行状态跃迁与系统告警。',
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 16),
        if (notifications.isEmpty)
          GlassCard(
            padding: const EdgeInsets.all(16),
            child: Text(
              '当前没有新的全局通知。',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          )
        else
          Column(
            children: [
              for (var index = 0; index < notifications.length; index++) ...[
                _NotificationCard(
                  notification: notifications[index],
                  onMarkRead: () => onMarkRead(notifications[index].id),
                  onDismiss: () => onDismiss(notifications[index].id),
                  onOpenOperation:
                      notifications[index].relatedOperationId == null
                      ? null
                      : () => onOpenOperation(
                          notifications[index].relatedOperationId!,
                        ),
                ),
                if (index < notifications.length - 1)
                  const SizedBox(height: 12),
              ],
            ],
          ),
      ],
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({
    required this.notification,
    required this.onMarkRead,
    required this.onDismiss,
    this.onOpenOperation,
  });

  final ShellRuntimeNotification notification;
  final VoidCallback onMarkRead;
  final VoidCallback onDismiss;
  final VoidCallback? onOpenOperation;

  @override
  Widget build(BuildContext context) {
    final isUnread = !notification.isRead;
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _ToneDot(tone: notification.tone, emphasized: isUnread),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(notification.title, style: AppTextStyles.labelMedium),
                    const SizedBox(height: 6),
                    Text(
                      notification.message,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              if (isUnread)
                Container(
                  width: 8,
                  height: 8,
                  margin: const EdgeInsets.only(top: 6),
                  decoration: const BoxDecoration(
                    color: AppColors.primary,
                    shape: BoxShape.circle,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MetaChip(label: _kindLabel(notification.kind)),
              if (notification.sourceTab != null)
                _MetaChip(label: _tabLabel(notification.sourceTab!)),
              _MetaChip(
                label: _formatTime(notification.createdAt),
                foreground: AppColors.textSecondary,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (onOpenOperation != null)
                OutlinedButton.icon(
                  onPressed: () {
                    onMarkRead();
                    onOpenOperation!();
                  },
                  icon: const Icon(Icons.travel_explore_rounded),
                  label: const Text('查看运行'),
                ),
              if (isUnread)
                TextButton.icon(
                  onPressed: onMarkRead,
                  icon: const Icon(Icons.mark_email_read_rounded),
                  label: const Text('标记已读'),
                ),
              TextButton.icon(
                onPressed: onDismiss,
                icon: const Icon(Icons.close_rounded),
                label: const Text('移除'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _kindLabel(ShellRuntimeNotificationKind kind) {
    switch (kind) {
      case ShellRuntimeNotificationKind.action:
        return '控制动作';
      case ShellRuntimeNotificationKind.session:
        return '运行状态';
      case ShellRuntimeNotificationKind.alert:
        return '系统告警';
      case ShellRuntimeNotificationKind.runtime:
        return '运行时快照';
    }
  }

  String _tabLabel(WorkbenchTab tab) {
    switch (tab) {
      case WorkbenchTab.operationsHub:
        return '概览';
      case WorkbenchTab.modeling:
        return '能源优化';
      case WorkbenchTab.dataAnalysis:
        return '数据分析';
      case WorkbenchTab.aiLab:
        return 'AI Lab';
      case WorkbenchTab.historyAudit:
        return '历史与审计';
    }
  }

  String _formatTime(DateTime value) {
    final local = value.toLocal();
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label, this.foreground = AppColors.primary});

  final String label;
  final Color foreground;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.bodySmall.copyWith(color: foreground),
      ),
    );
  }
}

class _ToneDot extends StatelessWidget {
  const _ToneDot({required this.tone, required this.emphasized});

  final ShellActionTone tone;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: emphasized ? 12 : 10,
      height: emphasized ? 12 : 10,
      margin: const EdgeInsets.only(top: 4),
      decoration: BoxDecoration(
        color: _colorForTone(tone),
        shape: BoxShape.circle,
      ),
    );
  }

  Color _colorForTone(ShellActionTone tone) {
    switch (tone) {
      case ShellActionTone.success:
        return AppColors.success;
      case ShellActionTone.warning:
        return AppColors.warning;
      case ShellActionTone.error:
        return AppColors.error;
      case ShellActionTone.info:
        return AppColors.primary;
    }
  }
}
