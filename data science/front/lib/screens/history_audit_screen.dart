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
import '../widgets/history/history_asset_ledger.dart';
import '../widgets/history/history_disposition_board.dart';
import '../widgets/history/audit_event_stream.dart';
import '../widgets/history/history_record_card.dart';
import '../widgets/history/history_state_sections.dart';
import '../widgets/operations/duty_section_block.dart';
import '../widgets/operations/decision_layout.dart';
import '../widgets/operations/incident_runbook_board.dart';
import '../widgets/operations/workbench_page_frame.dart';
import '../widgets/operations/workspace_action_lane.dart';
import '../widgets/navigation/main_shell_runtime_scope.dart';
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
  DashboardSummary? get _sharedSummary => widget.sharedRuntimeManaged
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
      _refreshSharedProjection(),
      _jobsViewModel.loadJobs(),
      _auditViewModel.loadActivity(),
      _historyViewModel.loadHistory(limit: 30),
    ]);
  }

  Future<void> _refreshSharedProjection() async {
    if (widget.sharedRuntimeManaged) {
      final runtime = MainShellRuntimeScope.maybeOf(context);
      if (runtime != null) {
        await runtime.refreshSharedSnapshot(force: true);
        return;
      }
    }
    await _dashboardViewModel.loadSummary();
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
                    description: '审计页直接复用驾驶舱链路处置清单，把快速回放、失败筛选和值班动作压成统一处置视图。',
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
                  DecisionHeaderCard(
                    title: '历史与审计',
                    summary: '先筛选异常，再在时间线和资产台账之间切换，最后再进入具体工作台。',
                    metrics: [
                      DecisionHeaderMetric(
                        label: '审计活动',
                        value: '${activity.length}',
                        helper: '当前筛选结果',
                        accent: AppColors.primary,
                        icon: Icons.timeline_rounded,
                      ),
                      DecisionHeaderMetric(
                        label: '历史记录',
                        value: '${_historyViewModel.records.length}',
                        helper: '可回放资产',
                        accent: AppColors.cta,
                        icon: Icons.inventory_2_rounded,
                      ),
                      DecisionHeaderMetric(
                        label: '当前筛选',
                        value:
                            '${_selectedType ?? "全部类型"} / ${_selectedStatus ?? "全部状态"}',
                        helper: '筛选范围',
                        accent: AppColors.warning,
                        icon: Icons.filter_alt_rounded,
                      ),
                      DecisionHeaderMetric(
                        label: '失败链路',
                        value:
                            '${summary?.assetSummary.failureChains.length ?? 0}',
                        helper: '优先关注异常',
                        accent: AppColors.error,
                        icon: Icons.error_outline_rounded,
                      ),
                    ],
                    primaryAction: DecisionHeaderAction(
                      label: '刷新审计流',
                      icon: Icons.refresh_rounded,
                      onTap: _refreshAll,
                      isPrimary: true,
                    ),
                    banner: DecisionBanner(
                      title: _selectedStatus == null
                          ? '默认查看全量记录'
                          : '当前已锁定 ${_selectedStatus == "failed"
                                ? "失败"
                                : _selectedStatus == "running"
                                ? "运行中"
                                : _selectedStatus!} 记录',
                      message:
                          (summary?.dutySummary.focusWatch ?? '').isNotEmpty
                          ? summary!.dutySummary.focusWatch
                          : '首屏只保留筛选条、最近异常时间线和资产台账预览，处置面板与长列表全部下沉。',
                      accent: _selectedStatus == 'failed'
                          ? AppColors.error
                          : AppColors.primary,
                      icon: _selectedStatus == 'failed'
                          ? Icons.error_outline_rounded
                          : Icons.fact_check_rounded,
                    ),
                  ),
                  const SizedBox(height: 20),
                  PrimaryWorkflowPanel(
                    eyebrow: '筛选条 + 双视图',
                    title: '当前筛选与双视图',
                    summary: '用一组筛选条锁定问题，再分别看最近异常时间线和资产台账预览。',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: [
                            FilledButton.tonalIcon(
                              onPressed: () =>
                                  _applyFilters(type: null, status: 'failed'),
                              icon: const Icon(Icons.error_outline_rounded),
                              label: const Text('仅看失败'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed: () =>
                                  _applyFilters(type: null, status: 'running'),
                              icon: const Icon(Icons.autorenew_rounded),
                              label: const Text('仅看运行中'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () =>
                                  _applyFilters(type: null, status: null),
                              icon: const Icon(Icons.filter_alt_off_rounded),
                              label: const Text('清空筛选'),
                            ),
                            for (final type in const [
                              ('analysis', '分析'),
                              ('ml_train', '训练'),
                              ('rag_ingest', 'RAG'),
                              ('optimization', '优化'),
                            ])
                              ChoiceChip(
                                label: Text(type.$2),
                                selected: _selectedType == type.$1,
                                onSelected: (_) => _applyFilters(
                                  type: _selectedType == type.$1
                                      ? null
                                      : type.$1,
                                  status: _selectedStatus,
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        LayoutBuilder(
                          builder: (context, constraints) {
                            final stacked = constraints.maxWidth < 1040;
                            final recentActivity = activity
                                .take(4)
                                .toList(growable: false);
                            final recentRecords = _historyViewModel.records
                                .take(4)
                                .toList(growable: false);

                            Widget buildTimeline() {
                              return _HistorySnapshotCard(
                                title: '最近异常时间线',
                                subtitle: '优先查看最近 4 条活动，避免先掉进长列表。',
                                icon: Icons.timeline_rounded,
                                child: recentActivity.isEmpty
                                    ? const Text('当前筛选下没有新的审计活动。')
                                    : Column(
                                        children: recentActivity
                                            .map(
                                              (item) => Padding(
                                                padding: const EdgeInsets.only(
                                                  bottom: 12,
                                                ),
                                                child: _HistoryLineItem(
                                                  title: item.title,
                                                  subtitle:
                                                      '${item.action} · ${item.source}',
                                                  detail: item.status,
                                                  accent:
                                                      item.severity == 'error'
                                                      ? AppColors.error
                                                      : item.severity ==
                                                            'warning'
                                                      ? AppColors.warning
                                                      : AppColors.primary,
                                                ),
                                              ),
                                            )
                                            .toList(growable: false),
                                      ),
                              );
                            }

                            Widget buildLedger() {
                              return _HistorySnapshotCard(
                                title: '资产台账预览',
                                subtitle: '只保留最近 4 条可回放资产，避免首屏重复出现多组跳转按钮。',
                                icon: Icons.inventory_2_rounded,
                                child: recentRecords.isEmpty
                                    ? const Text('当前还没有可回放的历史资产。')
                                    : Column(
                                        children: recentRecords
                                            .map(
                                              (record) => Padding(
                                                padding: const EdgeInsets.only(
                                                  bottom: 12,
                                                ),
                                                child: _HistoryLineItem(
                                                  title: record.filename,
                                                  subtitle:
                                                      record.createdAt == null
                                                      ? '等待时间戳'
                                                      : '${record.createdAt}',
                                                  detail:
                                                      record.storageUrl ??
                                                      '未生成存储路径',
                                                  accent: AppColors.cta,
                                                ),
                                              ),
                                            )
                                            .toList(growable: false),
                                      ),
                              );
                            }

                            if (stacked) {
                              return Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  buildTimeline(),
                                  const SizedBox(height: 16),
                                  buildLedger(),
                                ],
                              );
                            }

                            return Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Expanded(flex: 6, child: buildTimeline()),
                                const SizedBox(width: 16),
                                Expanded(flex: 5, child: buildLedger()),
                              ],
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  ProgressiveDetailSection(
                    title: '运营详情',
                    summary: '处置流、资产台账、事件流和完整记录列表统一收在这里。',
                    icon: Icons.dashboard_customize_rounded,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        for (var i = 0; i < orderedSections.length; i++) ...[
                          orderedSections[i].value,
                          if (i < orderedSections.length - 1)
                            const SizedBox(height: 20),
                        ],
                      ],
                    ),
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
    final chain = findChainSummary(_sharedSummary?.assetSummary, key);
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
    final chainSummary = _sharedSummary?.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((item) => item?.key == chain.key, orElse: () => null);
    final context = buildLaunchContextFromChain(
      chainSummary,
      prefix: chain.label,
    );
    final sourceLabel = context != null
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

class _HistorySnapshotCard extends StatelessWidget {
  const _HistorySnapshotCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.child,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Widget child;

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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: AppColors.primary),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: AppTextStyles.h4)),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}

class _HistoryLineItem extends StatelessWidget {
  const _HistoryLineItem({
    required this.title,
    required this.subtitle,
    required this.detail,
    required this.accent,
  });

  final String title;
  final String subtitle;
  final String detail;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTextStyles.labelLarge),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            detail,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.bodyMedium.copyWith(color: accent),
          ),
        ],
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
