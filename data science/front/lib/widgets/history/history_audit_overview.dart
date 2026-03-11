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
    this.assetSummary,
    required this.activityCount,
    required this.recordCount,
    required this.selectedType,
    required this.selectedStatus,
    required this.onTypeChanged,
    required this.onStatusChanged,
    required this.onClearFilters,
  });

  final DashboardKpis? kpis;
  final List<JobRecord> jobs;
  final AssetSummary? assetSummary;
  final int activityCount;
  final int recordCount;
  final String? selectedType;
  final String? selectedStatus;
  final ValueChanged<String?> onTypeChanged;
  final ValueChanged<String?> onStatusChanged;
  final VoidCallback onClearFilters;

  @override
  Widget build(BuildContext context) {
    final runningJobs = jobs.where((job) => job.isRunning).length;
    final failedJobs = jobs.where((job) => job.status == 'failed').length;
    final completedJobs = jobs.where((job) => job.status == 'succeeded').length;
    final latestJob = jobs.isEmpty ? null : jobs.first;
    final focusChain = assetSummary?.chainSummaries.isEmpty ?? true
        ? null
        : ([
            ...assetSummary!.chainSummaries,
          ]..sort((a, b) => b.priorityScore.compareTo(a.priorityScore))).first;

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
                  color: AppColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(
                  Icons.space_dashboard_rounded,
                  color: AppColors.primary,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('值班概览', style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '把筛选上下文、队列健康和审计覆盖收在一个控制板里，减少在审计页主路径里的重复摘要卡。',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _AuditKpiChip(
                label: '24h 作业',
                value: '${kpis?.jobs24h ?? 0}',
                color: AppColors.primary,
              ),
              _AuditKpiChip(
                label: '运行中',
                value: '$runningJobs',
                color: AppColors.warning,
              ),
              _AuditKpiChip(
                label: '失败',
                value: '$failedJobs',
                color: AppColors.error,
              ),
              _AuditKpiChip(
                label: '已完成',
                value: '$completedJobs',
                color: AppColors.success,
              ),
              _AuditKpiChip(
                label: '活动',
                value: '$activityCount',
                color: AppColors.cta,
              ),
              _AuditKpiChip(
                label: '记录',
                value: '$recordCount',
                color: AppColors.primary,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Current watch', style: AppTextStyles.labelMedium),
                const SizedBox(height: 6),
                Text(
                  focusChain != null
                      ? '${focusChain.workspaceTargetLabel} · ${focusChain.workspaceBrief}'
                      : latestJob == null
                      ? '当前暂无最新任务，重点关注筛选上下文和资产链路处置。'
                      : '${latestJob.displayTitle} · ${latestJob.statusMessage ?? latestJob.status}',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (focusChain != null)
                      _AuditContextChip(
                        label: '工作台',
                        value: focusChain.workspaceTargetLabel,
                      ),
                    if (focusChain != null)
                      _AuditContextChip(
                        label: '值班',
                        value: focusChain.incidentTargetLabel,
                      ),
                    _AuditContextChip(
                      label: '类型',
                      value: _typeLabel(selectedType),
                    ),
                    _AuditContextChip(
                      label: '状态',
                      value: _statusLabel(selectedStatus),
                    ),
                    _AuditContextChip(
                      label: '覆盖',
                      value: _coverageLabel(
                        activityCount: activityCount,
                        recordCount: recordCount,
                        failedJobs: kpis?.failedJobs ?? 0,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text('筛选控制', style: AppTextStyles.labelLarge),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _AuditFilterChip(
                label: '全部类型',
                selected: selectedType == null,
                onSelected: () => onTypeChanged(null),
              ),
              _AuditFilterChip(
                label: '优化',
                selected: selectedType == 'optimization',
                onSelected: () => onTypeChanged('optimization'),
              ),
              _AuditFilterChip(
                label: '分析',
                selected: selectedType == 'analysis',
                onSelected: () => onTypeChanged('analysis'),
              ),
              _AuditFilterChip(
                label: '训练',
                selected: selectedType == 'ml_train',
                onSelected: () => onTypeChanged('ml_train'),
              ),
              _AuditFilterChip(
                label: 'RAG',
                selected: selectedType == 'rag_ingest',
                onSelected: () => onTypeChanged('rag_ingest'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _AuditFilterChip(
                label: '全部状态',
                selected: selectedStatus == null,
                onSelected: () => onStatusChanged(null),
              ),
              _AuditFilterChip(
                label: '运行中',
                selected: selectedStatus == 'running',
                onSelected: () => onStatusChanged('running'),
              ),
              _AuditFilterChip(
                label: '已完成',
                selected: selectedStatus == 'succeeded',
                onSelected: () => onStatusChanged('succeeded'),
              ),
              _AuditFilterChip(
                label: '失败',
                selected: selectedStatus == 'failed',
                onSelected: () => onStatusChanged('failed'),
              ),
              OutlinedButton.icon(
                onPressed: onClearFilters,
                icon: const Icon(Icons.filter_alt_off_rounded),
                label: const Text('清空'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AuditKpiChip extends StatelessWidget {
  const _AuditKpiChip({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(width: 8),
          Text(value, style: AppTextStyles.labelLarge.copyWith(color: color)),
        ],
      ),
    );
  }
}

class _AuditContextChip extends StatelessWidget {
  const _AuditContextChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        '$label · $value',
        style: AppTextStyles.labelMedium.copyWith(
          color: AppColors.textSecondary,
        ),
      ),
    );
  }
}

class _AuditFilterChip extends StatelessWidget {
  const _AuditFilterChip({
    required this.label,
    required this.selected,
    required this.onSelected,
  });

  final String label;
  final bool selected;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => onSelected(),
      selectedColor: AppColors.infoLight,
      labelStyle: AppTextStyles.labelMedium.copyWith(
        color: selected ? AppColors.primary : AppColors.textSecondary,
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
