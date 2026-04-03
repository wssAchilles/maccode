/// Live operation console board for Operations Hub.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../viewmodels/operation_console_view_model.dart';
import '../common/glass_card.dart';
import 'duty_section_block.dart';
import 'job_event_timeline.dart';

class OperationConsoleBoard extends StatelessWidget {
  const OperationConsoleBoard({
    super.key,
    required this.viewModel,
    this.onApprove,
    this.onReject,
    this.onRetry,
    this.onCancel,
  });

  final OperationConsoleViewModel viewModel;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;
  final VoidCallback? onRetry;
  final VoidCallback? onCancel;

  @override
  Widget build(BuildContext context) {
    final operation = viewModel.selectedOperation;
    return DutySectionBlock(
      title: '运行控制台',
      subtitle: '实时查看当前选中的 Operation 执行轨迹、审批状态和产物发布。',
      trailing: Wrap(
        spacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          if (viewModel.isStreaming) _StatusPill.live(),
          if (viewModel.isLoading)
            const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          if (operation != null)
            IconButton(
              tooltip: '清除选中',
              onPressed: viewModel.clearSelection,
              icon: const Icon(Icons.close_rounded),
            ),
        ],
      ),
      child: operation == null
          ? _EmptyOperationConsole(errorMessage: viewModel.errorMessage)
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (viewModel.errorMessage != null) ...[
                  _ErrorBanner(message: viewModel.errorMessage!),
                  const SizedBox(height: 12),
                ],
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${operation.displayTitle} · ${operation.operationId ?? operation.jobId}',
                                  style: AppTextStyles.labelLarge,
                                ),
                                const SizedBox(height: 8),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: [
                                    _StatusPill(
                                      label: operation.status.toUpperCase(),
                                      foreground: _statusColor(
                                        operation.status,
                                      ),
                                      background: _statusBackground(
                                        operation.status,
                                      ),
                                    ),
                                    if (operation.controlTaskId?.isNotEmpty ==
                                        true)
                                      _NeutralPill(
                                        label:
                                            'ControlTask · ${operation.controlTaskId}',
                                      ),
                                    if (operation.trigger?.isNotEmpty == true)
                                      _NeutralPill(
                                        label: 'Trigger · ${operation.trigger}',
                                      ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          if (viewModel.isActing)
                            const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      LinearProgressIndicator(
                        value: operation.progress.clamp(0, 100) / 100,
                        minHeight: 8,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          _MetricChip(
                            label: '进度',
                            value: '${operation.progress}%',
                          ),
                          _MetricChip(
                            label: '步骤',
                            value: operation.currentStep == null
                                ? '--'
                                : '${operation.currentStep!.phase} · ${operation.currentStep!.toolName}',
                          ),
                          _MetricChip(
                            label: '产物',
                            value: '${operation.artifacts.length}',
                          ),
                          _MetricChip(
                            label: '事件',
                            value: '${operation.events.length}',
                          ),
                        ],
                      ),
                      if (operation.metrics.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: operation.metrics.entries
                              .take(4)
                              .map((entry) {
                                return _NeutralPill(
                                  label: '${entry.key} · ${entry.value}',
                                );
                              })
                              .toList(growable: false),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                JobEventTimeline(
                  job: operation,
                  title: '运行时间线',
                  onRetry: operation.retryable && onRetry != null
                      ? onRetry
                      : null,
                  onCancel:
                      !operation.isTerminal && !operation.isAwaitingApproval
                      ? onCancel
                      : null,
                  onApprove: operation.isAwaitingApproval ? onApprove : null,
                  onReject: operation.isAwaitingApproval ? onReject : null,
                ),
              ],
            ),
    );
  }
}

class _EmptyOperationConsole extends StatelessWidget {
  const _EmptyOperationConsole({this.errorMessage});

  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            errorMessage ?? '从审批中心或规划任务板选择一个运行实例，即可进入实时控制台。',
            style: AppTextStyles.bodyMedium.copyWith(
              color: errorMessage == null
                  ? AppColors.textSecondary
                  : AppColors.error,
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.errorLight,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.18)),
      ),
      child: Text(
        message,
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 2),
          Text(value, style: AppTextStyles.labelMedium),
        ],
      ),
    );
  }
}

class _NeutralPill extends StatelessWidget {
  const _NeutralPill({required this.label});

  final String label;

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
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({
    required this.label,
    required this.foreground,
    required this.background,
  });

  factory _StatusPill.live() => const _StatusPill(
    label: 'SSE LIVE',
    foreground: AppColors.success,
    background: AppColors.successLight,
  );

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

Color _statusColor(String status) {
  switch (status) {
    case 'succeeded':
      return AppColors.success;
    case 'failed':
    case 'cancelled':
      return AppColors.error;
    case 'awaiting_approval':
      return AppColors.warning;
    default:
      return AppColors.primary;
  }
}

Color _statusBackground(String status) {
  switch (status) {
    case 'succeeded':
      return AppColors.successLight;
    case 'failed':
    case 'cancelled':
      return AppColors.errorLight;
    case 'awaiting_approval':
      return AppColors.warningLight;
    default:
      return AppColors.infoLight;
  }
}
