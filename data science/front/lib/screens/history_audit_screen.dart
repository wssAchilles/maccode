/// 历史与审计页
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../config/app_theme.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../viewmodels/audit_view_model.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/history_view_model.dart';
import '../viewmodels/job_view_model.dart';
import '../widgets/common/glass_card.dart';
import '../widgets/history/history_audit_overview.dart';
import '../widgets/history/history_record_card.dart';
import '../widgets/history/history_state_sections.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/responsive_wrapper.dart';
import 'analysis_detail_screen.dart';

class HistoryAuditScreen extends StatefulWidget {
  const HistoryAuditScreen({
    super.key,
    this.dashboardViewModel,
    this.embedded = false,
  });

  final DashboardViewModel? dashboardViewModel;
  final bool embedded;

  @override
  State<HistoryAuditScreen> createState() => _HistoryAuditScreenState();
}

class _HistoryAuditScreenState extends State<HistoryAuditScreen> {
  late final DashboardViewModel _dashboardViewModel;
  late final bool _ownsDashboardViewModel;
  late final JobViewModel _jobsViewModel;
  late final AuditViewModel _auditViewModel;
  late final HistoryViewModel _historyViewModel;
  String? _selectedType;
  String? _selectedStatus;

  @override
  void initState() {
    super.initState();
    _dashboardViewModel = widget.dashboardViewModel ?? DashboardViewModel();
    _ownsDashboardViewModel = widget.dashboardViewModel == null;
    _dashboardViewModel.initialize();
    _jobsViewModel = JobViewModel(limit: 20);
    _auditViewModel = AuditViewModel();
    _historyViewModel = HistoryViewModel();
    _jobsViewModel.loadJobs();
    _auditViewModel.initialize();
    _historyViewModel.initialize();
  }

  @override
  void dispose() {
    if (_ownsDashboardViewModel) {
      _dashboardViewModel.dispose();
    }
    _jobsViewModel.dispose();
    _auditViewModel.dispose();
    _historyViewModel.dispose();
    super.dispose();
  }

  Future<void> _refreshAll() async {
    await Future.wait([
      _dashboardViewModel.loadSummary(),
      _jobsViewModel.loadJobs(),
      _auditViewModel.loadActivity(),
      _historyViewModel.loadHistory(limit: 50),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([
        _dashboardViewModel,
        _jobsViewModel,
        _auditViewModel,
        _historyViewModel,
      ]),
      builder: (context, _) {
        final summary = _dashboardViewModel.summary;
        final activity = _auditViewModel.activity;
        final content = RefreshIndicator(
          onRefresh: _refreshAll,
          child: ResponsiveWrapper(
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (widget.embedded) ...[
                    _EmbeddedAuditHeader(onRefresh: _refreshAll),
                    const SizedBox(height: 20),
                  ],
                  _buildSummary(summary),
                  const SizedBox(height: 20),
                  HistoryAuditOverview(
                    kpis: summary?.kpis,
                    jobs: _jobsViewModel.jobs,
                    activityCount: activity.length,
                    recordCount: _historyViewModel.records.length,
                    selectedType: _selectedType,
                    selectedStatus: _selectedStatus,
                  ),
                  const SizedBox(height: 20),
                  _buildFilters(),
                  const SizedBox(height: 20),
                  Text('任务审计', style: AppTextStyles.h4),
                  const SizedBox(height: 12),
                  JobActivityList(
                    jobs: _jobsViewModel.jobs,
                    emptyMessage: '当前过滤条件下暂无任务。',
                  ),
                  const SizedBox(height: 24),
                  Text('最近活动', style: AppTextStyles.h4),
                  const SizedBox(height: 12),
                  if (_auditViewModel.isLoading)
                    const HistoryLoadingState()
                  else if (_auditViewModel.errorMessage != null)
                    HistoryErrorState(
                      message: _auditViewModel.errorMessage!,
                      onRetry: () => _auditViewModel.loadActivity(),
                    )
                  else if (activity.isEmpty)
                    const _EmptyAuditSection(message: '暂无活动记录')
                  else
                    Column(
                      children: activity
                          .map(
                            (item) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: _AuditActivityCard(activity: item),
                            ),
                          )
                          .toList(growable: false),
                    ),
                  const SizedBox(height: 24),
                  Text('分析记录', style: AppTextStyles.h4),
                  const SizedBox(height: 12),
                  if (_historyViewModel.isLoading)
                    const HistoryLoadingState()
                  else if (_historyViewModel.errorMessage != null)
                    HistoryErrorState(
                      message: _historyViewModel.errorMessage!,
                      onRetry: () => _historyViewModel.loadHistory(limit: 50),
                    )
                  else if (_historyViewModel.records.isEmpty)
                    const HistoryEmptyState()
                  else
                    Column(
                      children: _historyViewModel.records
                          .map(
                            (record) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: HistoryRecordCard(
                                record: record,
                                isDeleting: _historyViewModel.isDeleting(
                                  record.id,
                                ),
                                onOpen: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) =>
                                          AnalysisDetailScreen(record: record),
                                    ),
                                  );
                                },
                                onDelete: () async {
                                  await _historyViewModel.deleteRecord(
                                    record.id,
                                  );
                                },
                              ),
                            ),
                          )
                          .toList(growable: false),
                    ),
                ],
              ),
            ),
          ),
        );

        if (widget.embedded) {
          return content;
        }

        return Scaffold(
          backgroundColor: AppColors.background,
          appBar: AppBar(
            title: const Text('历史与审计'),
            backgroundColor: AppColors.surface,
            surfaceTintColor: Colors.transparent,
            actions: [
              IconButton(
                onPressed: _refreshAll,
                icon: const Icon(Icons.refresh_rounded),
              ),
            ],
          ),
          body: content,
        );
      },
    );
  }

  Widget _buildSummary(DashboardSummary? summary) {
    final kpis = summary?.kpis;
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        _AuditMetric(label: '失败任务', value: '${kpis?.failedJobs ?? 0}'),
        _AuditMetric(label: '24h 作业', value: '${kpis?.jobs24h ?? 0}'),
        _AuditMetric(
          label: '审计活动',
          value: '${_auditViewModel.activity.length}',
        ),
        _AuditMetric(
          label: '分析记录',
          value: '${_historyViewModel.records.length}',
        ),
      ],
    );
  }

  Widget _buildFilters() {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('筛选', style: AppTextStyles.h4),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _FilterChip(
                label: '全部类型',
                selected: _selectedType == null,
                onSelected: () =>
                    _applyFilters(type: null, status: _selectedStatus),
              ),
              _FilterChip(
                label: '优化',
                selected: _selectedType == 'optimization',
                onSelected: () => _applyFilters(
                  type: 'optimization',
                  status: _selectedStatus,
                ),
              ),
              _FilterChip(
                label: '分析',
                selected: _selectedType == 'analysis',
                onSelected: () =>
                    _applyFilters(type: 'analysis', status: _selectedStatus),
              ),
              _FilterChip(
                label: '训练',
                selected: _selectedType == 'ml_train',
                onSelected: () =>
                    _applyFilters(type: 'ml_train', status: _selectedStatus),
              ),
              _FilterChip(
                label: 'RAG',
                selected: _selectedType == 'rag_ingest',
                onSelected: () =>
                    _applyFilters(type: 'rag_ingest', status: _selectedStatus),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _FilterChip(
                label: '全部状态',
                selected: _selectedStatus == null,
                onSelected: () =>
                    _applyFilters(type: _selectedType, status: null),
              ),
              _FilterChip(
                label: '运行中',
                selected: _selectedStatus == 'running',
                onSelected: () =>
                    _applyFilters(type: _selectedType, status: 'running'),
              ),
              _FilterChip(
                label: '已完成',
                selected: _selectedStatus == 'succeeded',
                onSelected: () =>
                    _applyFilters(type: _selectedType, status: 'succeeded'),
              ),
              _FilterChip(
                label: '失败',
                selected: _selectedStatus == 'failed',
                onSelected: () =>
                    _applyFilters(type: _selectedType, status: 'failed'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _applyFilters({String? type, String? status}) {
    setState(() {
      _selectedType = type;
      _selectedStatus = status;
    });
    _jobsViewModel.applyFilters(jobType: type, statusFilter: status);
    _auditViewModel.applyFilters(type: type, status: status);
  }
}

class _AuditMetric extends StatelessWidget {
  const _AuditMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: SizedBox(
        width: 160,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: AppTextStyles.labelMedium),
            const SizedBox(height: 6),
            Text(value, style: AppTextStyles.h4),
          ],
        ),
      ),
    );
  }
}

class _EmbeddedAuditHeader extends StatelessWidget {
  const _EmbeddedAuditHeader({required this.onRefresh});

  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('历史与审计', style: AppTextStyles.h2),
                const SizedBox(height: 8),
                Text(
                  '统一查看任务轨迹、系统活动和分析记录，便于排障和审计追踪。',
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          FilledButton.tonalIcon(
            onPressed: onRefresh,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('刷新'),
          ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
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

class _AuditActivityCard extends StatelessWidget {
  const _AuditActivityCard({required this.activity});

  final AuditActivity activity;

  @override
  Widget build(BuildContext context) {
    final color = switch (activity.severity) {
      'error' => AppColors.error,
      'warning' => AppColors.warning,
      _ => AppColors.primary,
    };
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Icon(Icons.timeline_rounded, color: color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(activity.title, style: AppTextStyles.labelLarge),
                const SizedBox(height: 4),
                Text(
                  '来源: ${activity.source} · 状态: ${activity.status}',
                  style: AppTextStyles.bodySmall,
                ),
                if (activity.details.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    activity.details.toString(),
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            activity.createdAt == null
                ? '--'
                : DateFormat(
                    'MM-dd HH:mm',
                  ).format(activity.createdAt!.toLocal()),
            style: AppTextStyles.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _EmptyAuditSection extends StatelessWidget {
  const _EmptyAuditSection({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
      ),
      child: Text(message, style: AppTextStyles.bodyMedium),
    );
  }
}
