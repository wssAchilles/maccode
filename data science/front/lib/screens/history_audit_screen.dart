/// 历史与审计页
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/data_analysis_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/history_record.dart';
import '../models/job_record.dart';
import '../models/main_shell_projection.dart';
import '../models/optimization_launch_intent.dart';
import '../utils/asset_chain_context.dart';
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
import '../widgets/operations/duty_section_block.dart';
import '../widgets/operations/embedded_page_header.dart';
import '../widgets/operations/incident_runbook_board.dart';
import '../widgets/operations/workbench_page_frame.dart';
import '../widgets/operations/workbench_command_strip.dart';
import '../widgets/operations/workspace_action_lane.dart';
import '../widgets/responsive_wrapper.dart';
import 'analysis_detail_screen.dart';

class HistoryAuditScreen extends StatefulWidget {
  const HistoryAuditScreen({
    super.key,
    this.dashboardViewModel,
    this.jobsViewModel,
    this.auditViewModel,
    this.historyViewModel,
    this.shellProjection,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
    this.isActive = true,
    this.sharedRuntimeManaged = false,
    this.surfaceMode = WorkbenchSurfaceMode.standalone,
  });

  final DashboardViewModel? dashboardViewModel;
  final JobViewModel? jobsViewModel;
  final AuditViewModel? auditViewModel;
  final HistoryViewModel? historyViewModel;
  final MainShellProjection? shellProjection;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;
  final bool isActive;
  final bool sharedRuntimeManaged;
  final WorkbenchSurfaceMode surfaceMode;

  @override
  State<HistoryAuditScreen> createState() => _HistoryAuditScreenState();
}

class _HistoryAuditScreenState extends State<HistoryAuditScreen> {
  late final DashboardViewModel _dashboardViewModel;
  late final bool _ownsDashboardViewModel;
  late final JobViewModel _jobsViewModel;
  late final bool _ownsJobsViewModel;
  late final AuditViewModel _auditViewModel;
  late final bool _ownsAuditViewModel;
  late final HistoryViewModel _historyViewModel;
  late final bool _ownsHistoryViewModel;
  String? _selectedType;
  String? _selectedStatus;
  bool _didActivateWorkspace = false;
  DashboardSummary? get _sharedSummary =>
      widget.sharedRuntimeManaged
          ? (widget.shellProjection?.summary ?? _dashboardViewModel.summary)
          : _dashboardViewModel.summary;

  @override
  void initState() {
    super.initState();
    _dashboardViewModel = widget.dashboardViewModel ?? DashboardViewModel();
    _ownsDashboardViewModel = widget.dashboardViewModel == null;
    _jobsViewModel = widget.jobsViewModel ?? JobViewModel(limit: 20);
    _ownsJobsViewModel = widget.jobsViewModel == null;
    _auditViewModel = widget.auditViewModel ?? AuditViewModel();
    _ownsAuditViewModel = widget.auditViewModel == null;
    _historyViewModel = widget.historyViewModel ?? HistoryViewModel();
    _ownsHistoryViewModel = widget.historyViewModel == null;
    _handleWorkspaceActivation(widget.isActive);
  }

  @override
  void didUpdateWidget(covariant HistoryAuditScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isActive != oldWidget.isActive) {
      _handleWorkspaceActivation(widget.isActive);
    }
  }

  @override
  void dispose() {
    if (_ownsDashboardViewModel) {
      _dashboardViewModel.dispose();
    }
    if (_ownsJobsViewModel) {
      _jobsViewModel.dispose();
    }
    if (_ownsAuditViewModel) {
      _auditViewModel.dispose();
    }
    if (_ownsHistoryViewModel) {
      _historyViewModel.dispose();
    }
    super.dispose();
  }

  void _handleWorkspaceActivation(bool isActive) {
    if (!widget.sharedRuntimeManaged) {
      _jobsViewModel.setWorkspaceActive(isActive);
    }
    if (!isActive) {
      return;
    }
    if (!_didActivateWorkspace) {
      _didActivateWorkspace = true;
      if (!widget.sharedRuntimeManaged) {
        _dashboardViewModel.initialize();
        _jobsViewModel.loadJobs();
      }
      _auditViewModel.initialize();
      _historyViewModel.initialize();
    }
  }

  Future<void> _refreshAll() async {
    await Future.wait([
      _dashboardViewModel.loadSummary(),
      _jobsViewModel.loadJobs(),
      _auditViewModel.loadActivity(),
      _historyViewModel.loadHistory(limit: 30),
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
        final summary = _sharedSummary;
        final activity = _auditViewModel.activity;
        final orderedSections =
            <MapEntry<String, Widget>>[
              if ((summary?.assetSummary.governance.isNotEmpty ?? false))
                MapEntry(
                  'disposition',
                  HistoryDispositionBoard(
                    assetSummary: summary!.assetSummary,
                    dutySummary: summary.dutySummary,
                    jobs: _jobsViewModel.jobs,
                    records: _historyViewModel.records,
                    trailing:
                        _isHistoryFocusSection(
                          'disposition',
                          summary.dutySummary,
                        )
                        ? _historyDutyFocusChip()
                        : null,
                    onGovernanceAction: _handleGovernanceAction,
                    onFailureAction: _handleFailureChainAction,
                    onFilterFailures: _handleFailureFilter,
                    onReplayAction: _handleReplayAction,
                  ),
                ),
              if ((summary?.assetSummary.governance.isNotEmpty ?? false))
                MapEntry(
                  'runbook',
                  IncidentRunbookBoard(
                    summary: summary!.assetSummary,
                    title: '处置清单',
                    description:
                        '审计页直接复用驾驶舱链路处置清单，把快速回放、失败筛选和值班动作压成统一处置视图。',
                    dutySummary: summary.dutySummary,
                    trailing:
                        _isHistoryFocusSection('runbook', summary.dutySummary)
                        ? _historyDutyFocusChip()
                        : null,
                    onOpenChain: (chain) {
                      _openChainSummary(chain, prefix: '处置清单');
                    },
                  ),
                ),
              MapEntry(
                'ledger',
                DutySectionBlock(
                  title: '资产台账与联动',
                  subtitle: '统一查看资产库存、风险联动、矩阵回放和资产台账入口。',
                  trailing:
                      _isHistoryFocusSection('ledger', summary?.dutySummary)
                      ? _historyDutyFocusChip()
                      : null,
                  child: HistoryAssetLedger(
                    jobs: _jobsViewModel.jobs,
                    records: _historyViewModel.records,
                    assetSummary: summary?.assetSummary,
                    dutySummary: summary?.dutySummary,
                    alerts: summary?.alerts ?? const <DashboardAlert>[],
                    onOpenAiLab: widget.onOpenAiLab,
                    onOpenDataAnalysis: widget.onOpenDataAnalysis,
                    onOpenOptimization: widget.onOpenOptimization,
                  ),
                ),
              ),
              MapEntry(
                'event_stream',
                (_auditViewModel.isLoading || _jobsViewModel.isLoading)
                    ? DutySectionBlock(
                        title: '统一审计事件流',
                        subtitle: '把任务执行和审计活动合并到同一条时间线里，减少并行维护两套列表。',
                        trailing:
                            _isHistoryFocusSection(
                              'event_stream',
                              summary?.dutySummary,
                            )
                            ? _historyDutyFocusChip()
                            : null,
                        child: const HistoryLoadingState(),
                      )
                    : _auditViewModel.errorMessage != null
                    ? DutySectionBlock(
                        title: '统一审计事件流',
                        subtitle: '把任务执行和审计活动合并到同一条时间线里，减少并行维护两套列表。',
                        trailing:
                            _isHistoryFocusSection(
                              'event_stream',
                              summary?.dutySummary,
                            )
                            ? _historyDutyFocusChip()
                            : null,
                        child: HistoryErrorState(
                          message: _auditViewModel.errorMessage!,
                          onRetry: () => _auditViewModel.loadActivity(),
                        ),
                      )
                    : AuditEventStream(
                        jobs: _jobsViewModel.jobs,
                        activity: activity,
                        assetSummary: summary?.assetSummary,
                        dutySummary: summary?.dutySummary,
                        trailing:
                            _isHistoryFocusSection(
                              'event_stream',
                              summary?.dutySummary,
                            )
                            ? _historyDutyFocusChip()
                            : null,
                        onOpenChain: _openChainWorkspace,
                        onOpenChainSummary: (chain) {
                          _openChainSummary(chain, prefix: '统一审计事件流');
                        },
                        onFilterFailures: _handleFailureFilter,
                      ),
              ),
              MapEntry(
                'records',
                DutySectionBlock(
                  title: '分析记录',
                  subtitle: '查看分析沉淀记录，并继续进入详情或删除清理。',
                  trailing:
                      _isHistoryFocusSection('records', summary?.dutySummary)
                      ? _historyDutyFocusChip()
                      : null,
                  child: _historyViewModel.isLoading
                      ? const HistoryLoadingState()
                      : _historyViewModel.errorMessage != null
                      ? HistoryErrorState(
                          message: _historyViewModel.errorMessage!,
                          onRetry: () =>
                              _historyViewModel.loadHistory(limit: 30),
                        )
                      : _historyViewModel.records.isEmpty
                      ? const HistoryEmptyState()
                      : Column(
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
                                              AnalysisDetailScreen(
                                                record: record,
                                              ),
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
                ),
              ),
            ]..sort(
              (a, b) => compareSectionKeysByDutyFocus(
                a.key,
                b.key,
                summary?.dutySummary,
                _historySectionFocusOrder,
              ),
            );
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
                    dutySummary: summary?.dutySummary,
                    assetSummary: summary?.assetSummary,
                    dutyActions: summary?.dutySummary.auditActions ?? const [],
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
                    onDutyAction: _handleDutyAction,
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
                  for (var i = 0; i < orderedSections.length; i++) ...[
                    orderedSections[i].value,
                    if (i < orderedSections.length - 1)
                      const SizedBox(height: 20),
                  ],
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
    final chain = _sharedSummary?.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((entry) => entry?.key == item.key, orElse: () => null);
    final context = buildLaunchContextFromChain(chain, prefix: '风险处置中心');
    switch (item.key) {
      case 'dataset':
        _applyFilters(
          type: 'analysis',
          status: item.failedJobs > 0 ? 'failed' : null,
        );
        widget.onOpenDataAnalysis?.call(
          DataAnalysisLaunchIntent.workspace(
            sourceLabel: sourceLabel,
            context: context,
          ),
        );
        break;
      case 'model':
        _applyFilters(
          type: 'ml_train',
          status: item.failedJobs > 0 ? 'failed' : null,
        );
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.deepLearning(
            '',
            sourceLabel: sourceLabel,
            context: context,
          ),
        );
        break;
      case 'knowledge':
        _applyFilters(
          type: 'rag_ingest',
          status: item.failedJobs > 0 ? 'failed' : null,
        );
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel, context: context),
        );
        break;
      case 'optimization':
        _applyFilters(
          type: 'optimization',
          status: item.failedJobs > 0 ? 'failed' : null,
        );
        widget.onOpenOptimization?.call(
          OptimizationLaunchIntent(sourceLabel: sourceLabel, context: context),
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

  void _handleDutyAction(DutyAction action) {
    switch (action.command) {
      case 'open_workspace':
        final chain = _sharedSummary?.assetSummary.chainSummaries
            .cast<AssetChainSummary?>()
            .firstWhere(
              (item) => item?.key == action.chainKey,
              orElse: () => null,
            );
        if (chain != null) {
          final context = buildLaunchContextFromDutyAction(
            action,
            prefix: '值班动作',
          );
          final sourceLabel = context.sourceLabel;
          switch (chain.key) {
            case 'dataset':
              widget.onOpenDataAnalysis?.call(
                DataAnalysisLaunchIntent.workspace(
                  sourceLabel: sourceLabel,
                  context: context,
                ),
              );
              return;
            case 'model':
              widget.onOpenAiLab?.call(
                AiLabLaunchIntent.deepLearning(
                  '',
                  sourceLabel: sourceLabel,
                  context: context,
                ),
              );
              return;
            case 'knowledge':
              widget.onOpenAiLab?.call(
                AiLabLaunchIntent.rag(
                  '',
                  sourceLabel: sourceLabel,
                  context: context,
                ),
              );
              return;
            case 'optimization':
              widget.onOpenOptimization?.call(
                OptimizationLaunchIntent(
                  sourceLabel: sourceLabel,
                  context: context,
                ),
              );
              return;
          }
          return;
        }
        _openChainWorkspace(action.chainKey);
        return;
      case 'filter_failed':
        _applyFilterForChain(action.chainKey, 'failed');
        return;
      case 'filter_running':
        _applyFilterForChain(action.chainKey, 'running');
        return;
      case 'clear_filters':
        _applyFilters(type: null, status: null);
        return;
    }
  }

  void _applyFilterForChain(String key, String status) {
    switch (key) {
      case 'dataset':
        _applyFilters(type: 'analysis', status: status);
        return;
      case 'model':
        _applyFilters(type: 'ml_train', status: status);
        return;
      case 'knowledge':
        _applyFilters(type: 'rag_ingest', status: status);
        return;
      case 'optimization':
        _applyFilters(type: 'optimization', status: status);
        return;
      default:
        _applyFilters(type: null, status: status);
    }
  }

  void _openChainWorkspace(String key) {
    final sourceLabel = _chainSourceLabel(key, prefix: '统一审计事件流');
    final chain = _sharedSummary?.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == key, orElse: () => null);
    final context = buildLaunchContextFromChain(chain, prefix: '统一审计事件流');
    switch (key) {
      case 'dataset':
        widget.onOpenDataAnalysis?.call(
          DataAnalysisLaunchIntent.workspace(
            sourceLabel: sourceLabel,
            context: context,
          ),
        );
        break;
      case 'model':
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.deepLearning(
            '',
            sourceLabel: sourceLabel,
            context: context,
          ),
        );
        break;
      case 'knowledge':
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel, context: context),
        );
        break;
      case 'optimization':
        widget.onOpenOptimization?.call(
          OptimizationLaunchIntent(sourceLabel: sourceLabel, context: context),
        );
        break;
    }
  }

  void _openChainSummary(AssetChainSummary chain, {required String prefix}) {
    final context = buildLaunchContextFromChain(chain, prefix: prefix);
    final sourceLabel = buildChainSourceLabel(
      chain,
      prefix: prefix,
      includeWorkspaceBrief: true,
    );
    switch (chain.key) {
      case 'dataset':
        widget.onOpenDataAnalysis?.call(
          DataAnalysisLaunchIntent.workspace(
            sourceLabel: sourceLabel,
            context: context,
          ),
        );
        break;
      case 'model':
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.deepLearning(
            '',
            sourceLabel: sourceLabel,
            context: context,
          ),
        );
        break;
      case 'knowledge':
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel, context: context),
        );
        break;
      case 'optimization':
        widget.onOpenOptimization?.call(
          OptimizationLaunchIntent(sourceLabel: sourceLabel, context: context),
        );
        break;
    }
  }

  void _handleReplayAction(String key) {
    final chain = findChainSummary(
      _sharedSummary?.assetSummary,
      key,
    );
    switch (key) {
      case 'dataset':
        final context = buildLaunchContext(
          sourceLabel: '回放最新',
          chain: chain,
          workspaceTarget: 'data_governance',
          cardTarget: 'current_asset',
          incidentTarget: 'asset',
          workspaceBrief: '历史分析资产已载入当前资产',
          watchSummary: '优先核对当前资产质量与结果摘要',
        );
        final record = _latestReplayableRecord();
        if (record != null) {
          widget.onOpenDataAnalysis?.call(
            DataAnalysisLaunchIntent.fromHistoryRecord(
              record,
              sourceLabel: buildWorkbenchSourceLabel(context, prefix: '回放最新'),
              context: context,
            ),
          );
        }
        break;
      case 'model':
        final context = buildLaunchContext(
          sourceLabel: '回放最新',
          chain: chain,
          workspaceTarget: 'ai_runtime',
          cardTarget: 'runtime_product',
          incidentTarget: 'runtime',
          workspaceBrief: '训练产物已回填到训练入口',
          watchSummary: '优先核对训练配置和最新模型产物',
        );
        final job = _latestReplayableTrainingJob();
        if (job != null) {
          widget.onOpenAiLab?.call(
            AiLabLaunchIntent.fromTrainingJob(
              job,
              sourceLabel: buildWorkbenchSourceLabel(context, prefix: '回放最新'),
              context: context,
            ),
          );
        }
        break;
      case 'knowledge':
        final context = buildLaunchContext(
          sourceLabel: '回放最新',
          chain: chain,
          workspaceTarget: 'ai_runtime',
          cardTarget: 'runtime_product',
          incidentTarget: 'runtime',
          workspaceBrief: '知识快照已回填到知识入口',
          watchSummary: '优先核对集合配置和最新知识快照',
        );
        final job = _latestReplayableKnowledgeJob();
        if (job != null) {
          widget.onOpenAiLab?.call(
            AiLabLaunchIntent.fromRagJob(
              job,
              sourceLabel: buildWorkbenchSourceLabel(context, prefix: '回放最新'),
              context: context,
            ),
          );
        }
        break;
      case 'optimization':
        final context = buildLaunchContext(
          sourceLabel: '回放最新',
          chain: chain,
          workspaceTarget: 'optimization_registry',
          cardTarget: 'latest_snapshot',
          incidentTarget: 'asset',
          workspaceBrief: '优化快照已载入结果工作台',
          watchSummary: '优先核对最新快照与结果摘要',
        );
        final job = _latestReplayableOptimizationJob();
        if (job != null) {
          widget.onOpenOptimization?.call(
            OptimizationLaunchIntent.fromJob(
              job,
              sourceLabel: buildWorkbenchSourceLabel(context, prefix: '回放最新'),
              context: context,
            ),
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
    final chainSummary = _sharedSummary
        ?.assetSummary
        .chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == chain.key, orElse: () => null);
    final context = buildLaunchContextFromChain(
      chainSummary,
      prefix: chain.label,
    );
    final sourceLabel =
        context != null
        ? buildWorkbenchSourceLabel(context, prefix: chain.label)
        : chain.label;
    switch (chain.key) {
      case 'dataset':
        _applyFilters(type: 'analysis', status: 'failed');
        widget.onOpenDataAnalysis?.call(
          DataAnalysisLaunchIntent.workspace(
            sourceLabel: sourceLabel,
            context: context,
          ),
        );
        break;
      case 'model':
        _applyFilters(type: 'ml_train', status: 'failed');
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.deepLearning(
            '',
            sourceLabel: sourceLabel,
            context: context,
          ),
        );
        break;
      case 'knowledge':
        _applyFilters(type: 'rag_ingest', status: 'failed');
        widget.onOpenAiLab?.call(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel, context: context),
        );
        break;
      case 'optimization':
        _applyFilters(type: 'optimization', status: 'failed');
        widget.onOpenOptimization?.call(
          OptimizationLaunchIntent(sourceLabel: sourceLabel, context: context),
        );
        break;
    }
  }

  String _chainSourceLabel(String key, {required String prefix}) {
    final chain = _sharedSummary?.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == key, orElse: () => null);
    if (chain == null) {
      return prefix;
    }
    return buildChainSourceLabel(
      chain,
      prefix: prefix,
      includeWorkspaceBrief: true,
    );
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

const Map<String, List<String>> _historySectionFocusOrder = {
  'data_governance': [
    'ledger',
    'disposition',
    'event_stream',
    'records',
    'runbook',
  ],
  'data_handoff': [
    'disposition',
    'ledger',
    'event_stream',
    'records',
    'runbook',
  ],
  'ai_runtime': ['disposition', 'runbook', 'ledger', 'event_stream', 'records'],
  'ai_assets': ['ledger', 'disposition', 'runbook', 'event_stream', 'records'],
  'optimization_operations': [
    'disposition',
    'runbook',
    'event_stream',
    'ledger',
    'records',
  ],
  'optimization_registry': [
    'ledger',
    'disposition',
    'runbook',
    'event_stream',
    'records',
  ],
  'audit_center': [
    'event_stream',
    'disposition',
    'runbook',
    'ledger',
    'records',
  ],
};

bool _isHistoryFocusSection(String key, DutySummary? summary) {
  return isDutyFocusSection(key, summary, _historySectionFocusOrder);
}

Widget _historyDutyFocusChip() {
  return const WorkspaceStatusChip(
    label: '值班焦点',
    icon: Icons.center_focus_strong_rounded,
    foreground: AppColors.primary,
    background: AppColors.infoLight,
  );
}
