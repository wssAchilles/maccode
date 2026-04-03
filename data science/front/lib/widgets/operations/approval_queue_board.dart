/// Approval queue board for operations hub.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import '../common/glass_card.dart';
import 'duty_section_block.dart';

class ApprovalQueueBoard extends StatelessWidget {
  const ApprovalQueueBoard({
    super.key,
    required this.jobs,
    required this.isLoading,
    required this.onRefresh,
    required this.onApprove,
    required this.onReject,
    required this.isUpdating,
    this.onOpenDetails,
    this.errorMessage,
  });

  final List<JobRecord> jobs;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback onRefresh;
  final ValueChanged<JobRecord> onApprove;
  final ValueChanged<JobRecord> onReject;
  final bool Function(String jobId) isUpdating;
  final ValueChanged<JobRecord>? onOpenDetails;

  @override
  Widget build(BuildContext context) {
    return DutySectionBlock(
      title: '审批中心',
      subtitle: '集中处理需要人工批准的高风险运行任务。',
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
          if (jobs.isNotEmpty) ...[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _SummaryChip(label: '待审批', value: '${jobs.length}'),
                _SummaryChip(
                  label: '高风险原因',
                  value:
                      '${jobs.where((job) => (job.approvalPolicy?['reason'] ?? '').toString().trim().isNotEmpty).length}',
                ),
                _SummaryChip(
                  label: '涉及控制任务',
                  value:
                      '${jobs.map((job) => job.controlTaskId).whereType<String>().toSet().length}',
                ),
              ],
            ),
            const SizedBox(height: 12),
          ],
          if (errorMessage != null) ...[
            Text(
              errorMessage!,
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('刷新队列'),
            ),
            const SizedBox(height: 12),
          ],
          if (jobs.isEmpty && !isLoading)
            GlassCard(
              padding: const EdgeInsets.all(16),
              child: Text(
                '当前没有待审批运行。',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            )
          else
            Column(
              children: [
                for (var index = 0; index < jobs.length; index++) ...[
                  _ApprovalCard(
                    job: jobs[index],
                    isUpdating: isUpdating(jobs[index].jobId),
                    onApprove: () => onApprove(jobs[index]),
                    onReject: () => onReject(jobs[index]),
                    onOpenDetails: onOpenDetails == null
                        ? null
                        : () => onOpenDetails!(jobs[index]),
                  ),
                  if (index < jobs.length - 1) const SizedBox(height: 12),
                ],
              ],
            ),
        ],
      ),
    );
  }
}

class _ApprovalCard extends StatelessWidget {
  const _ApprovalCard({
    required this.job,
    required this.isUpdating,
    required this.onApprove,
    required this.onReject,
    this.onOpenDetails,
  });

  final JobRecord job;
  final bool isUpdating;
  final VoidCallback onApprove;
  final VoidCallback onReject;
  final VoidCallback? onOpenDetails;

  @override
  Widget build(BuildContext context) {
    final reason = (job.approvalPolicy?['reason'] ?? '').toString().trim();
    final currentStep = job.currentStep;
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(job.displayTitle, style: AppTextStyles.labelLarge),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppColors.warningLight,
                  borderRadius: BorderRadius.circular(
                    AppDecorations.radiusFull,
                  ),
                ),
                child: Text(
                  '待审批',
                  style: AppTextStyles.labelMedium.copyWith(
                    color: AppColors.warning,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            job.jobId,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (currentStep != null) ...[
            const SizedBox(height: 10),
            Text(
              '当前步骤 · ${currentStep.phase} · ${currentStep.toolName}',
              style: AppTextStyles.bodySmall,
            ),
          ],
          if (reason.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              '审批原因 · $reason',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.icon(
                onPressed: isUpdating ? null : onApprove,
                icon: isUpdating
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.check_circle_outline),
                label: Text(isUpdating ? '处理中' : '批准执行'),
              ),
              OutlinedButton.icon(
                onPressed: isUpdating ? null : onReject,
                icon: const Icon(Icons.cancel_outlined),
                label: const Text('驳回任务'),
              ),
              if (onOpenDetails != null)
                TextButton.icon(
                  onPressed: onOpenDetails,
                  icon: const Icon(Icons.travel_explore_rounded),
                  label: const Text('查看运行'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryChip extends StatelessWidget {
  const _SummaryChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        '$label · $value',
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
      ),
    );
  }
}
