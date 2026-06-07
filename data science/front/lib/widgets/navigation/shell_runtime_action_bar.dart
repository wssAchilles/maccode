library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/main_shell_projection.dart';

class ShellRuntimeActionBar extends StatelessWidget {
  const ShellRuntimeActionBar({
    super.key,
    required this.projection,
    required this.onOpenApprovals,
    required this.onOpenOperations,
    required this.onOpenNotifications,
    required this.onShowUserInfo,
    required this.onSignOut,
    this.compact = false,
    this.enableAccountActions = true,
  });

  final MainShellProjection projection;
  final VoidCallback onOpenApprovals;
  final VoidCallback onOpenOperations;
  final VoidCallback onOpenNotifications;
  final VoidCallback onShowUserInfo;
  final VoidCallback onSignOut;
  final bool compact;
  final bool enableAccountActions;

  @override
  Widget build(BuildContext context) {
    final operation = projection.selectedOperation;
    final operationLabel = operation == null
        ? (compact ? '运行' : '运行控制台')
        : compact
        ? '运行 · ${operation.status}'
        : '${operation.displayTitle} · ${operation.status.toUpperCase()}';

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.end,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        FilledButton.tonalIcon(
          onPressed: onOpenApprovals,
          icon: const Icon(Icons.pending_actions_rounded),
          label: Text(
            compact
                ? '审批 ${projection.pendingApprovalCount}'
                : '审批中心 · ${projection.pendingApprovalCount}',
          ),
        ),
        OutlinedButton.icon(
          onPressed: onOpenOperations,
          icon: Icon(
            operation == null
                ? Icons.monitor_heart_outlined
                : Icons.play_circle_outline_rounded,
          ),
          label: Text(operationLabel),
        ),
        OutlinedButton.icon(
          onPressed: onOpenNotifications,
          icon: Icon(
            projection.unreadNotificationCount > 0
                ? Icons.notifications_active_outlined
                : Icons.notifications_none_rounded,
          ),
          label: Text(
            compact
                ? '通知 ${projection.unreadNotificationCount}'
                : '通知中心 · ${projection.unreadNotificationCount}',
          ),
        ),
        if (projection.hasActiveAction)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.primaryLight,
              borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            ),
            child: Text(
              projection.activeActionLabel,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        OutlinedButton.icon(
          key: const ValueKey('main-nav-user-info'),
          onPressed: enableAccountActions ? onShowUserInfo : null,
          icon: const Icon(Icons.account_circle_outlined),
          label: Text(compact ? '用户' : '用户信息'),
        ),
        FilledButton.tonalIcon(
          key: const ValueKey('main-nav-sign-out'),
          onPressed: enableAccountActions ? onSignOut : null,
          icon: const Icon(Icons.logout_rounded),
          style: FilledButton.styleFrom(foregroundColor: AppColors.textPrimary),
          label: Text(compact ? '退出' : '退出登录'),
        ),
      ],
    );
  }
}
