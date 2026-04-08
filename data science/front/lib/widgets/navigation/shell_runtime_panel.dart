library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import '../../models/main_shell_projection.dart';
import '../../models/workbench_runtime_models.dart';
import '../../viewmodels/approval_queue_view_model.dart';
import '../../viewmodels/operation_console_view_model.dart';
import '../operations/approval_queue_board.dart';
import '../operations/operation_console_board.dart';
import 'shell_notification_center_panel.dart';
import 'shell_runtime_projection_banner.dart';

class ShellRuntimePanel extends StatelessWidget {
  const ShellRuntimePanel({
    super.key,
    required this.projection,
    required this.panelKind,
    required this.approvalQueueViewModel,
    required this.operationConsoleViewModel,
    required this.onSelectPanel,
    required this.onClose,
    required this.onApproveQueued,
    required this.onRejectQueued,
    required this.onOpenOperation,
    required this.onOpenOperationId,
    required this.onApproveSelected,
    required this.onRejectSelected,
    required this.onRetrySelected,
    required this.onCancelSelected,
    required this.onMarkNotificationRead,
    required this.onMarkAllNotificationsRead,
    required this.onDismissNotification,
  });

  final MainShellProjection projection;
  final ShellRuntimePanelKind panelKind;
  final ApprovalQueueViewModel approvalQueueViewModel;
  final OperationConsoleViewModel operationConsoleViewModel;
  final ValueChanged<ShellRuntimePanelKind> onSelectPanel;
  final VoidCallback onClose;
  final ValueChanged<JobRecord> onApproveQueued;
  final ValueChanged<JobRecord> onRejectQueued;
  final ValueChanged<JobRecord> onOpenOperation;
  final ValueChanged<String> onOpenOperationId;
  final VoidCallback onApproveSelected;
  final VoidCallback onRejectSelected;
  final VoidCallback onRetrySelected;
  final VoidCallback onCancelSelected;
  final ValueChanged<String> onMarkNotificationRead;
  final VoidCallback onMarkAllNotificationsRead;
  final ValueChanged<String> onDismissNotification;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.surface,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(16, 16, 12, 12),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppColors.border)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Wrap(
                    spacing: 8,
                    children: [
                      _PanelChip(
                        label: '审批中心',
                        selected: panelKind == ShellRuntimePanelKind.approvals,
                        onTap: () =>
                            onSelectPanel(ShellRuntimePanelKind.approvals),
                      ),
                      _PanelChip(
                        label: '运行详情',
                        selected: panelKind == ShellRuntimePanelKind.operations,
                        onTap: () =>
                            onSelectPanel(ShellRuntimePanelKind.operations),
                      ),
                      _PanelChip(
                        label: '通知',
                        selected:
                            panelKind == ShellRuntimePanelKind.notifications,
                        onTap: () =>
                            onSelectPanel(ShellRuntimePanelKind.notifications),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: '关闭侧栏',
                  onPressed: onClose,
                  icon: const Icon(Icons.close_rounded),
                ),
              ],
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ShellRuntimeProjectionBanner(projection: projection),
                  const SizedBox(height: 16),
                  panelKind == ShellRuntimePanelKind.approvals
                      ? ApprovalQueueBoard(
                          jobs: approvalQueueViewModel.jobs,
                          isLoading: approvalQueueViewModel.isLoading,
                          errorMessage: approvalQueueViewModel.errorMessage,
                          onRefresh: approvalQueueViewModel.loadQueue,
                          onApprove: onApproveQueued,
                          onReject: onRejectQueued,
                          isUpdating: approvalQueueViewModel.isUpdating,
                          onOpenDetails: onOpenOperation,
                        )
                      : panelKind == ShellRuntimePanelKind.operations
                      ? OperationConsoleBoard(
                          viewModel: operationConsoleViewModel,
                          onApprove: onApproveSelected,
                          onReject: onRejectSelected,
                          onRetry: onRetrySelected,
                          onCancel: onCancelSelected,
                        )
                      : ShellNotificationCenterPanel(
                          notifications: projection.notifications,
                          onMarkAllRead: onMarkAllNotificationsRead,
                          onMarkRead: onMarkNotificationRead,
                          onDismiss: onDismissNotification,
                          onOpenOperation: (operationId) {
                            onSelectPanel(ShellRuntimePanelKind.operations);
                            onOpenOperationId(operationId);
                          },
                        ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PanelChip extends StatelessWidget {
  const _PanelChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => onTap(),
      selectedColor: AppColors.primaryLight,
      labelStyle: AppTextStyles.labelMedium.copyWith(
        color: selected ? AppColors.primary : AppColors.textSecondary,
      ),
    );
  }
}
