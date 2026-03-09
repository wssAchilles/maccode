/// 历史与审计概览板
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../models/job_record.dart';
import '../common/glass_card.dart';

class HistoryAuditOverview extends StatelessWidget {
  const HistoryAuditOverview({
    super.key,
    required this.kpis,
    required this.jobs,
    required this.activityCount,
    required this.recordCount,
    required this.selectedType,
    required this.selectedStatus,
  });

  final DashboardKpis? kpis;
  final List<JobRecord> jobs;
  final int activityCount;
  final int recordCount;
  final String? selectedType;
  final String? selectedStatus;

  @override
  Widget build(BuildContext context) {
    final runningJobs = jobs.where((job) => job.isRunning).length;
    final failedJobs = jobs.where((job) => job.status == 'failed').length;
    final completedJobs = jobs.where((job) => job.status == 'succeeded').length;
    final latestJob = jobs.isEmpty ? null : jobs.first;

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1080;
        final cards = [
          _AuditOverviewCard(
            title: '筛选上下文',
            subtitle: '明确当前审计视图锁定的是哪一类任务与状态。',
            accent: AppColors.primary,
            icon: Icons.tune_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _AuditMetricRow(label: '任务类型', value: _typeLabel(selectedType)),
                _AuditMetricRow(
                  label: '状态',
                  value: _statusLabel(selectedStatus),
                ),
                _AuditMetricRow(
                  label: '24h 作业',
                  value: '${kpis?.jobs24h ?? 0}',
                ),
              ],
            ),
          ),
          _AuditOverviewCard(
            title: '队列健康',
            subtitle: '快速识别运行中积压、失败任务和最近一次变化。',
            accent: failedJobs > 0 ? AppColors.warning : AppColors.success,
            icon: failedJobs > 0
                ? Icons.warning_amber_rounded
                : Icons.monitor_heart_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _AuditMetricRow(label: '运行中', value: '$runningJobs'),
                _AuditMetricRow(label: '已完成', value: '$completedJobs'),
                _AuditMetricRow(label: '失败', value: '$failedJobs'),
                _AuditMetricRow(
                  label: '最近任务',
                  value: latestJob == null
                      ? '暂无任务'
                      : '${latestJob.displayTitle} · '
                            '${latestJob.statusMessage ?? latestJob.status}',
                ),
              ],
            ),
          ),
          _AuditOverviewCard(
            title: '审计覆盖',
            subtitle: '衡量活动流、历史记录和失败项是否进入统一观测面。',
            accent: AppColors.cta,
            icon: Icons.fact_check_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _AuditMetricRow(label: '活动条目', value: '$activityCount'),
                _AuditMetricRow(label: '分析记录', value: '$recordCount'),
                _AuditMetricRow(
                  label: '失败任务',
                  value: '${kpis?.failedJobs ?? 0}',
                ),
                _AuditMetricRow(
                  label: '覆盖状态',
                  value: _coverageLabel(
                    activityCount: activityCount,
                    recordCount: recordCount,
                    failedJobs: kpis?.failedJobs ?? 0,
                  ),
                ),
              ],
            ),
          ),
        ];

        if (compact) {
          return Column(
            children: [
              for (var i = 0; i < cards.length; i++) ...[
                cards[i],
                if (i < cards.length - 1) const SizedBox(height: 12),
              ],
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (var i = 0; i < cards.length; i++) ...[
              Expanded(child: cards[i]),
              if (i < cards.length - 1) const SizedBox(width: 12),
            ],
          ],
        );
      },
    );
  }
}

class _AuditOverviewCard extends StatelessWidget {
  const _AuditOverviewCard({
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.icon,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Color accent;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: Icon(icon, color: accent, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}

class _AuditMetricRow extends StatelessWidget {
  const _AuditMetricRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 72,
            child: Text(
              label,
              style: AppTextStyles.labelMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

String _typeLabel(String? value) {
  switch (value) {
    case 'optimization':
      return '能源优化';
    case 'analysis':
      return '数据分析';
    case 'ml_train':
      return '模型训练';
    case 'rag_ingest':
      return '知识库构建';
    default:
      return '全部类型';
  }
}

String _statusLabel(String? value) {
  switch (value) {
    case 'running':
      return '运行中';
    case 'succeeded':
      return '已完成';
    case 'failed':
      return '失败';
    default:
      return '全部状态';
  }
}

String _coverageLabel({
  required int activityCount,
  required int recordCount,
  required int failedJobs,
}) {
  if (activityCount == 0 && recordCount == 0) {
    return '待积累';
  }
  if (failedJobs > 0) {
    return '需排障';
  }
  return '健康';
}
