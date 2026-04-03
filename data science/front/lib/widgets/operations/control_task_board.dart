/// Planning-layer control task board
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/control_task_record.dart';
import '../common/glass_card.dart';
import 'duty_section_block.dart';

class ControlTaskBoard extends StatelessWidget {
  const ControlTaskBoard({
    super.key,
    required this.tasks,
    required this.isLoading,
    required this.onRetry,
    required this.onRunTask,
    required this.isTaskRunning,
    required this.onToggleTask,
    required this.isTaskUpdating,
    required this.onToggleApproval,
    required this.onEditDefinition,
    this.errorMessage,
  });

  final List<ControlTaskRecord> tasks;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback onRetry;
  final ValueChanged<ControlTaskRecord> onRunTask;
  final bool Function(String controlTaskId) isTaskRunning;
  final ValueChanged<ControlTaskRecord> onToggleTask;
  final bool Function(String controlTaskId) isTaskUpdating;
  final ValueChanged<ControlTaskRecord> onToggleApproval;
  final ValueChanged<ControlTaskRecord> onEditDefinition;

  @override
  Widget build(BuildContext context) {
    return DutySectionBlock(
      title: '规划任务',
      subtitle: '把调度、审批与治理层定义从运行实例中分离出来，集中查看系统当前的计划任务。',
      trailing: isLoading
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (errorMessage != null) ...[
            _InfoBanner(message: errorMessage!, onRetry: onRetry),
            const SizedBox(height: 12),
          ],
          if (tasks.isEmpty && !isLoading)
            const _EmptyState()
          else
            Column(
              children: [
                for (var i = 0; i < tasks.length; i++) ...[
                  _ControlTaskTile(
                    task: tasks[i],
                    isRunning: isTaskRunning(tasks[i].id),
                    isUpdating: isTaskUpdating(tasks[i].id),
                    onRunTask: () => onRunTask(tasks[i]),
                    onToggleTask: () => onToggleTask(tasks[i]),
                    onToggleApproval: () => onToggleApproval(tasks[i]),
                    onEditDefinition: () => onEditDefinition(tasks[i]),
                  ),
                  if (i < tasks.length - 1) const SizedBox(height: 12),
                ],
              ],
            ),
        ],
      ),
    );
  }
}

class _ControlTaskTile extends StatelessWidget {
  const _ControlTaskTile({
    required this.task,
    required this.isRunning,
    required this.isUpdating,
    required this.onRunTask,
    required this.onToggleTask,
    required this.onToggleApproval,
    required this.onEditDefinition,
  });

  final ControlTaskRecord task;
  final bool isRunning;
  final bool isUpdating;
  final VoidCallback onRunTask;
  final VoidCallback onToggleTask;
  final VoidCallback onToggleApproval;
  final VoidCallback onEditDefinition;

  @override
  Widget build(BuildContext context) {
    final approvalMode = (task.approvalPolicy['mode'] ?? 'auto').toString();
    final requiredApproval = task.approvalPolicy['required'] == true;
    final approvalReason = (task.approvalPolicy['reason'] ?? '')
        .toString()
        .trim();
    final schedule = task.schedule?.trim();
    final dependencyLabel = task.dependencies.isEmpty
        ? '无依赖'
        : '${task.dependencies.length} 项依赖';

    return GlassCard(
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
                    Text(task.title, style: AppTextStyles.labelLarge),
                    const SizedBox(height: 6),
                    Text(
                      task.id,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              _Badge(
                label: task.enabled ? 'ACTIVE' : 'PAUSED',
                foreground: task.enabled
                    ? AppColors.success
                    : AppColors.warning,
                background: task.enabled
                    ? AppColors.successLight
                    : AppColors.warningLight,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _Badge(
                label: task.kind.toUpperCase(),
                foreground: AppColors.primary,
                background: AppColors.infoLight,
              ),
              _Badge(
                label: requiredApproval
                    ? '审批 ${approvalMode.toUpperCase()}'
                    : '审批 AUTO',
                foreground: requiredApproval
                    ? AppColors.warning
                    : AppColors.textPrimary,
                background: requiredApproval
                    ? AppColors.warningLight
                    : AppColors.surfaceVariant,
              ),
              _Badge(
                label: dependencyLabel,
                foreground: AppColors.textPrimary,
                background: AppColors.surfaceVariant,
              ),
            ],
          ),
          const SizedBox(height: 12),
          _DetailRow(
            label: '调度',
            value:
                schedule == null ||
                    schedule.isEmpty ||
                    schedule.toLowerCase() == 'manual'
                ? '手动触发'
                : schedule,
          ),
          if (task.operationType.isNotEmpty)
            _DetailRow(label: '运行类型', value: task.operationType),
          _DetailRow(
            label: '责任人',
            value: task.owner.isEmpty ? 'system' : task.owner,
          ),
          _DetailRow(
            label: '默认输入',
            value: task.defaultInput.isEmpty
                ? '无'
                : task.defaultInput.keys.take(3).join(' / '),
          ),
          if (task.dependencies.isNotEmpty)
            _DetailRow(
              label: '依赖',
              value: task.dependencies.take(3).join(' / '),
            ),
          if (approvalReason.isNotEmpty)
            _DetailRow(label: '审批原因', value: approvalReason),
          const SizedBox(height: 8),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.tonalIcon(
                onPressed: task.enabled && !isRunning ? onRunTask : null,
                icon: isRunning
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.play_arrow_rounded),
                label: Text(isRunning ? '触发中' : '立即运行'),
              ),
              OutlinedButton.icon(
                onPressed: !isUpdating ? onToggleTask : null,
                icon: isUpdating
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(
                        task.enabled
                            ? Icons.pause_circle_outline_rounded
                            : Icons.play_circle_outline_rounded,
                      ),
                label: Text(isUpdating ? '更新中' : (task.enabled ? '暂停' : '恢复')),
              ),
              OutlinedButton.icon(
                onPressed: !isUpdating ? onToggleApproval : null,
                icon: Icon(
                  requiredApproval
                      ? Icons.verified_user_outlined
                      : Icons.bolt_outlined,
                ),
                label: Text(
                  isUpdating ? '更新中' : (requiredApproval ? '改为自动' : '改为审批'),
                ),
              ),
              OutlinedButton.icon(
                onPressed: !isUpdating ? onEditDefinition : null,
                icon: const Icon(Icons.tune_rounded),
                label: Text(isUpdating ? '更新中' : '编辑定义'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 72,
            child: Text(
              label,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          Expanded(child: Text(value, style: AppTextStyles.bodySmall)),
        ],
      ),
    );
  }
}

class _Badge extends StatelessWidget {
  const _Badge({
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
        style: AppTextStyles.labelSmall.copyWith(
          color: foreground,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.2,
        ),
      ),
    );
  }
}

class _InfoBanner extends StatelessWidget {
  const _InfoBanner({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.warningLight,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: AppColors.warning.withValues(alpha: 0.24)),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.sync_problem_rounded,
            color: AppColors.warning,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
          ),
          const SizedBox(width: 8),
          TextButton(onPressed: onRetry, child: const Text('重试')),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        '当前暂无规划任务定义。',
        style: AppTextStyles.bodyMedium.copyWith(
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}
