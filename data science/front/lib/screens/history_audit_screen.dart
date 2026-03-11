/// 历史与审计页
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/data_analysis_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/history_record.dart';
import '../models/job_record.dart';
import '../models/optimization_launch_intent.dart';
import '../viewmodels/audit_view_model.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/history_view_model.dart';
import '../viewmodels/job_view_model.dart';
import '../widgets/history/history_audit_overview.dart';
import '../widgets/history/history_asset_ledger.dart';
import '../widgets/history/history_disposition_board.dart';
import '../widgets/history/audit_event_stream.dart';
import '../widgets/history/history_record_card.dart';
import '../widgets/history/history_state_sections.dart';
import '../widgets/operations/embedded_page_header.dart';
import '../widgets/operations/incident_runbook_board.dart';
import '../widgets/operations/workbench_page_frame.dart';
import '../widgets/operations/workbench_command_strip.dart';
import '../widgets/responsive_wrapper.dart';
import 'analysis_detail_screen.dart';

class HistoryAuditScreen extends StatefulWidget {
  const HistoryAuditScreen({
    super.key,
    this.dashboardViewModel,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
    this.surfaceMode = WorkbenchSurfaceMode.standalone,
  });

  final DashboardViewModel? dashboardViewModel;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;
  final WorkbenchSurfaceMode surfaceMode;

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
                  if (widget.surfaceMode.isEmbedded) ...[
                    _EmbeddedAuditHeader(onRefresh: _refreshAll),
                    const SizedBox(height: 20),
                  ],
                  HistoryAuditOverview(
                    kpis: summary?.kpis,
                    jobs: _jobsViewModel.jobs,
                    assetSummary: summary?.assetSummary,
                    activityCount: activity.length,
                    recordCount: _historyViewModel.records.length,
                    selectedType: _selectedType,
                    selectedStatus: _selectedStatus,
                    onTypeChanged: (type) {
                      _applyFilters(type: type, status: _selectedStatus);
                    },
                    onStatusChanged: (status) {
                      _applyFilters(type: _selectedType, status: status);
                    },
                    onClearFilters: () {
                      _applyFilters(type: null, status: null);
                    },
                  ),
                  const SizedBox(height: 20),
                  if ((summary?.assetSummary.governance.isNotEmpty ??
                      false)) ...[
                    HistoryDispositionBoard(
                      assetSummary: summary!.assetSummary,
                      jobs: _jobsViewModel.jobs,
                      records: _historyViewModel.records,
                      onGovernanceAction: _handleGovernanceAction,
                      onFailureAction: _handleFailureChainAction,
                      onFilterFailures: _handleFailureFilter,
                      onReplayAction: _handleReplayAction,
                    ),
                    const SizedBox(height: 20),
                    IncidentRunbookBoard(
                      summary: summary.assetSummary,
                      title: '处置 Runbook',
                      description:
                          '审计页直接复用驾驶舱链路 runbook，把快速回放、失败筛选和值班动作压成统一处置清单。',
                      onOpenChain: (chain) {
                        _openChainSummary(chain, prefix: '处置 Runbook');
                      },
                    ),
                    const SizedBox(height: 20),
                  ],
                  HistoryAssetLedger(
                    jobs: _jobsViewModel.jobs,
                    records: _historyViewModel.records,
                    assetSummary: summary?.assetSummary,
                    alerts: summary?.alerts ?? const <DashboardAlert>[],
                    onOpenAiLab: widget.onOpenAiLab,
                    onOpenDataAnalysis: widget.onOpenDataAnalysis,
                    onOpenOptimization: widget.onOpenOptimization,
                  ),
                  const SizedBox(height: 20),
                  WorkbenchCommandStrip(
                    title: '页级动作',
                    description: '把刷新和高频审计筛选固定在顶部，减少在单壳模式下依赖局部 AppBar 或长列表回滚。',
                    actions: [
                      WorkbenchCommandAction(
                        label: '刷新审计流',
                        icon: Icons.refresh_rounded,
                        onTap: () {
                          _refreshAll();
                        },
                        tone: WorkbenchCommandTone.primary,
                      ),
                      WorkbenchCommandAction(
                        label: '仅看失败',
                        icon: Icons.error_outline_rounded,
                        onTap: () {
                          _applyFilters(type: null, status: 'failed');
                        },
                        tone: WorkbenchCommandTone.tonal,
                      ),
                      WorkbenchCommandAction(
                        label: '仅看运行中',
                        icon: Icons.autorenew_rounded,
                        onTap: () {
                          _applyFilters(type: null, status: 'running');
                        },
                        tone: WorkbenchCommandTone.tonal,
                      ),
                      WorkbenchCommandAction(
                        label: '清空筛选',
                        icon: Icons.filter_alt_off_rounded,
                        onTap: () {
                          _applyFilters(type: null, status: null);
                        },
                        tone: WorkbenchCommandTone.outline,
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  if (_auditViewModel.isLoading || _jobsViewModel.isLoading)
                    const HistoryLoadingState()
                  else if (_auditViewModel.errorMessage != null)
                    HistoryErrorState(
                      message: _auditViewModel.errorMessage!,
                      onRetry: () => _auditViewModel.loadActivity(),
                    )
                  else
                    AuditEventStream(
                      jobs: _jobsViewModel.jobs,
                      activity: activity,
                      assetSummary: summary?.assetSummary,
                      onOpenChain: _openChainWorkspace,
                      onOpenChainSummary: (chain) {
                        _openChainSummary(chain, prefix: '统一审计事件流');
                      },
                      onFilterFailures: _handleFailureFilter,
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

        return WorkbenchPageFrame(
          surfaceMode: widget.surfaceMode,
          appBar: widget.surfaceMode.isStandalone
              ? AppBar(
                  title: const Text('历史与审计'),
                  backgroundColor: AppColors.surface,
                  surfaceTintColor: Colors.transparent,
                  actions: [
                    IconButton(
                      onPressed: _refreshAll,
                      icon: const Icon(Icons.refresh_rounded),
                    ),
                  ],
                )
              : null,
          body: content,
        );
      },
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

  void _handleGovernanceAction(AssetGovernanceItem item) {
    final sourceLabel = _chainSourceLabel(item.key, prefix: '风险处置中心');
    switch (item.key) {
      case 'dataset':
        _applyFilters(
          type: 'analysis',
          status: item.failedJobs > 0 ? 'failed' : null,
        );
        widget.onOpenDataAnalysis?.call(
          DataAnalysisLaunchIntent.workspace(sourceLabel: sourceLabel),
        );
        break;
      case 'model':
        _applyFilters(
          type: 'ml_train',
          status: item.failedJobs > 0 ? 'failed' : null,
        );
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.deepLearning('', sourceLabel: sourceLabel),
        );
        break;
      case 'knowledge':
        _applyFilters(
          type: 'rag_ingest',
          status: item.failedJobs > 0 ? 'failed' : null,
        );
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel),
        );
        break;
      case 'optimization':
        _applyFilters(
          type: 'optimization',
          status: item.failedJobs > 0 ? 'failed' : null,
        );
        widget.onOpenOptimization?.call(
          OptimizationLaunchIntent(sourceLabel: sourceLabel),
        );
        break;
    }
  }

  void _handleFailureFilter(String key) {
    switch (key) {
      case 'dataset':
        _applyFilters(type: 'analysis', status: 'failed');
        break;
      case 'model':
        _applyFilters(type: 'ml_train', status: 'failed');
        break;
      case 'knowledge':
        _applyFilters(type: 'rag_ingest', status: 'failed');
        break;
      case 'optimization':
        _applyFilters(type: 'optimization', status: 'failed');
        break;
    }
  }

  void _openChainWorkspace(String key) {
    final sourceLabel = _chainSourceLabel(key, prefix: '统一审计事件流');
    switch (key) {
      case 'dataset':
        widget.onOpenDataAnalysis?.call(
          DataAnalysisLaunchIntent.workspace(sourceLabel: sourceLabel),
        );
        break;
      case 'model':
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.deepLearning('', sourceLabel: sourceLabel),
        );
        break;
      case 'knowledge':
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel),
        );
        break;
      case 'optimization':
        widget.onOpenOptimization?.call(
          OptimizationLaunchIntent(sourceLabel: sourceLabel),
        );
        break;
    }
  }

  void _openChainSummary(AssetChainSummary chain, {required String prefix}) {
    final sourceLabel = [
      prefix,
      chain.label,
      chain.workspaceTargetLabel,
      chain.incidentTargetLabel,
      chain.focusLabel,
    ].join(' · ');
    switch (chain.key) {
      case 'dataset':
        widget.onOpenDataAnalysis?.call(
          DataAnalysisLaunchIntent.workspace(sourceLabel: sourceLabel),
        );
        break;
      case 'model':
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.deepLearning('', sourceLabel: sourceLabel),
        );
        break;
      case 'knowledge':
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel),
        );
        break;
      case 'optimization':
        widget.onOpenOptimization?.call(
          OptimizationLaunchIntent(sourceLabel: sourceLabel),
        );
        break;
    }
  }

  void _handleReplayAction(String key) {
    switch (key) {
      case 'dataset':
        final record = _latestReplayableRecord();
        if (record != null) {
          widget.onOpenDataAnalysis?.call(
            DataAnalysisLaunchIntent.fromHistoryRecord(record),
          );
        }
        break;
      case 'model':
        final job = _latestReplayableTrainingJob();
        if (job != null) {
          widget.onOpenAiLab?.call(AiLabLaunchIntent.fromTrainingJob(job));
        }
        break;
      case 'knowledge':
        final job = _latestReplayableKnowledgeJob();
        if (job != null) {
          widget.onOpenAiLab?.call(AiLabLaunchIntent.fromRagJob(job));
        }
        break;
      case 'optimization':
        final job = _latestReplayableOptimizationJob();
        if (job != null) {
          widget.onOpenOptimization?.call(
            OptimizationLaunchIntent.fromJob(job),
          );
        }
        break;
    }
  }

  HistoryRecord? _latestReplayableRecord() {
    for (final record in _historyViewModel.records) {
      if (record.summary != null || (record.storageUrl?.isNotEmpty ?? false)) {
        return record;
      }
    }
    return null;
  }

  JobRecord? _latestReplayableTrainingJob() {
    for (final job in _jobsViewModel.jobs) {
      if (job.type == 'ml_train' &&
          job.status == 'succeeded' &&
          (job.result['model_path']?.toString().isNotEmpty ?? false)) {
        return job;
      }
    }
    return null;
  }

  JobRecord? _latestReplayableKnowledgeJob() {
    for (final job in _jobsViewModel.jobs) {
      if (job.type == 'rag_ingest' &&
          job.status == 'succeeded' &&
          ((job.result['collection'] ?? job.input['collection_name'])
                  ?.toString()
                  .isNotEmpty ??
              false)) {
        return job;
      }
    }
    return null;
  }

  JobRecord? _latestReplayableOptimizationJob() {
    for (final job in _jobsViewModel.jobs) {
      if (job.type == 'optimization' &&
          job.status == 'succeeded' &&
          job.result.isNotEmpty) {
        return job;
      }
    }
    return null;
  }

  void _handleFailureChainAction(AssetFailureChain chain) {
    final sourceLabel = _chainSourceLabel(
      chain.key,
      prefix: '${chain.label} ${chain.jobId.substring(0, 8)}',
    );
    switch (chain.key) {
      case 'dataset':
        _applyFilters(type: 'analysis', status: 'failed');
        widget.onOpenDataAnalysis?.call(
          DataAnalysisLaunchIntent.workspace(sourceLabel: sourceLabel),
        );
        break;
      case 'model':
        _applyFilters(type: 'ml_train', status: 'failed');
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.deepLearning('', sourceLabel: sourceLabel),
        );
        break;
      case 'knowledge':
        _applyFilters(type: 'rag_ingest', status: 'failed');
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel),
        );
        break;
      case 'optimization':
        _applyFilters(type: 'optimization', status: 'failed');
        widget.onOpenOptimization?.call(
          OptimizationLaunchIntent(sourceLabel: sourceLabel),
        );
        break;
    }
  }

  String _chainSourceLabel(String key, {required String prefix}) {
    final chain = _dashboardViewModel.summary?.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == key, orElse: () => null);
    if (chain == null) {
      return prefix;
    }
    return [
      prefix,
      chain.label,
      chain.workspaceTargetLabel,
      chain.dispositionTargetLabel,
      chain.incidentTargetLabel,
    ].join(' · ');
  }
}

class _EmbeddedAuditHeader extends StatelessWidget {
  const _EmbeddedAuditHeader({required this.onRefresh});

  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return EmbeddedPageHeader(
      title: '历史与审计',
      description: '统一查看任务轨迹、系统活动和分析记录，便于排障和审计追踪。',
      trailing: FilledButton.tonalIcon(
        onPressed: onRefresh,
        icon: const Icon(Icons.refresh_rounded),
        label: const Text('刷新'),
      ),
    );
  }
}
