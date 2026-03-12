/// 历史与审计概览板
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../models/job_record.dart';
import '../../utils/asset_chain_context.dart';
import '../operations/duty_context_board.dart';

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

    return DutyContextBoard(
      title: '值班概览',
      description: '把筛选上下文、队列健康和审计覆盖收在一个控制板里，减少在审计页主路径里的重复摘要卡。',
      icon: Icons.space_dashboard_rounded,
      accent: AppColors.primary,
      metrics: [
        DutyMetric(
          label: '24h 作业',
          value: '${kpis?.jobs24h ?? 0}',
          color: AppColors.primary,
        ),
        DutyMetric(
          label: '运行中',
          value: '$runningJobs',
          color: AppColors.warning,
        ),
        DutyMetric(
          label: '失败',
          value: '$failedJobs',
          color: AppColors.error,
        ),
        DutyMetric(
          label: '已完成',
          value: '$completedJobs',
          color: AppColors.success,
        ),
        DutyMetric(
          label: '活动',
          value: '$activityCount',
          color: AppColors.cta,
        ),
        DutyMetric(
          label: '记录',
          value: '$recordCount',
          color: AppColors.primary,
        ),
      ],
      currentWatch: focusChain != null
          ? buildChainCurrentWatch(focusChain)
          : latestJob == null
          ? '当前暂无最新任务，重点关注筛选上下文和资产链路处置。'
          : '${latestJob.displayTitle} · ${latestJob.statusMessage ?? latestJob.status}',
      contextFacts: [
        if (focusChain != null)
          DutyContextFact(
            label: '工作台',
            value: focusChain.workspaceTargetLabel,
            icon: Icons.account_tree_rounded,
            foreground: AppColors.primary,
            background: AppColors.infoLight,
          ),
        if (focusChain != null)
          DutyContextFact(
            label: '卡片',
            value: focusChain.cardTargetLabel,
            icon: Icons.dashboard_customize_rounded,
          ),
        if (focusChain != null)
          DutyContextFact(
            label: '值班',
            value: focusChain.incidentTargetLabel,
            icon: Icons.priority_high_rounded,
            foreground: AppColors.warning,
            background: AppColors.warningLight,
          ),
        DutyContextFact(
          label: '类型',
          value: _typeLabel(selectedType),
          icon: Icons.category_rounded,
        ),
        DutyContextFact(
          label: '状态',
          value: _statusLabel(selectedStatus),
          icon: Icons.tune_rounded,
        ),
        DutyContextFact(
          label: '覆盖',
          value: _coverageLabel(
            activityCount: activityCount,
            recordCount: recordCount,
            failedJobs: kpis?.failedJobs ?? 0,
          ),
          icon: Icons.fact_check_rounded,
        ),
      ],
      footerTitle: '筛选控制',
      footer: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
