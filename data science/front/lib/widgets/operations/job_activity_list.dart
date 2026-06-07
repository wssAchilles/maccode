/// 最近任务流
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import 'job_progress_card.dart';

class JobActivityList extends StatelessWidget {
  const JobActivityList({
    super.key,
    required this.jobs,
    this.emptyMessage = '暂无任务记录',
    this.compact = false,
    this.onOpenJob,
  });

  final List<JobRecord> jobs;
  final String emptyMessage;
  final bool compact;
  final ValueChanged<JobRecord>? onOpenJob;

  @override
  Widget build(BuildContext context) {
    if (jobs.isEmpty) {
      return _JobEmptyState(message: emptyMessage);
    }

    return Column(
      children: jobs
          .map(
            (job) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: JobProgressCard(
                job: job,
                compact: compact,
                onOpenDetails: onOpenJob == null ? null : () => onOpenJob!(job),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _JobEmptyState extends StatelessWidget {
  const _JobEmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        message,
        style: AppTextStyles.bodyMedium.copyWith(
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}
