/// 工业驾驶舱概览页
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/data_analysis_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/optimization_launch_intent.dart';
import '../utils/asset_chain_context.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../widgets/operations/alert_panel.dart';
import '../widgets/operations/asset_governance_queue.dart';
import '../widgets/operations/asset_inventory_board.dart';
import '../widgets/operations/asset_version_timeline_board.dart';
import '../widgets/operations/dataset_asset_card.dart';
import '../widgets/operations/duty_context_board.dart';
import '../widgets/operations/duty_section_block.dart';
import '../widgets/operations/duty_signal_strip.dart';
import '../widgets/operations/embedded_page_header.dart';
import '../widgets/operations/incident_priority_strip.dart';
import '../widgets/operations/incident_runbook_board.dart';
import '../widgets/operations/model_status_card.dart';
import '../widgets/operations/operations_event_bus_board.dart';
import '../widgets/operations/operations_narrative_board.dart';
import '../widgets/operations/system_status_strip.dart';
import '../widgets/operations/workspace_action_lane.dart';
import '../widgets/operations/workbench_page_frame.dart';
import '../widgets/responsive_wrapper.dart';

class OperationsHubScreen extends StatefulWidget {
  const OperationsHubScreen({
    super.key,
    required this.viewModel,
    required this.onNavigateToTab,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
    this.surfaceMode = WorkbenchSurfaceMode.standalone,
  });

  final DashboardViewModel viewModel;
  final ValueChanged<int> onNavigateToTab;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;
  final WorkbenchSurfaceMode surfaceMode;

  @override
  State<OperationsHubScreen> createState() => _OperationsHubScreenState();
}

class _OperationsHubScreenState extends State<OperationsHubScreen> {
  @override
  void initState() {
    super.initState();
    widget.viewModel.initialize();
  }

  void _openChainWorkspace(AssetChainSummary chain, {required String source}) {
    final context = buildLaunchContextFromChain(chain, prefix: source);
    final sourceLabel = buildChainSourceLabel(
      chain,
      prefix: source,
      includeWorkspaceBrief: true,
    );
    switch (chain.key) {
      case 'dataset':
        final onOpenDataAnalysis = widget.onOpenDataAnalysis;
        if (onOpenDataAnalysis != null) {
          onOpenDataAnalysis(
            DataAnalysisLaunchIntent.workspace(
              sourceLabel: sourceLabel,
              context: context,
            ),
          );
        } else {
          widget.onNavigateToTab(2);
        }
        break;
      case 'model':
        final onOpenAiLab = widget.onOpenAiLab;
        if (onOpenAiLab != null) {
          onOpenAiLab(
            AiLabLaunchIntent.deepLearning(
              '',
              sourceLabel: sourceLabel,
              context: context,
            ),
          );
        } else {
          widget.onNavigateToTab(3);
        }
        break;
      case 'knowledge':
        final onOpenAiLab = widget.onOpenAiLab;
        if (onOpenAiLab != null) {
          onOpenAiLab(
            AiLabLaunchIntent.rag(
              '',
              sourceLabel: sourceLabel,
              context: context,
            ),
          );
        } else {
          widget.onNavigateToTab(3);
        }
        break;
      case 'optimization':
        final onOpenOptimization = widget.onOpenOptimization;
        if (onOpenOptimization != null) {
          onOpenOptimization(
            OptimizationLaunchIntent(sourceLabel: sourceLabel, context: context),
          );
        } else {
          widget.onNavigateToTab(1);
        }
        break;
      default:
        widget.onNavigateToTab(0);
    }
  }

  AssetChainSummary? _chainFor(DashboardSummary summary, String key) {
    return summary.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((chain) => chain?.key == key, orElse: () => null);
  }

  WorkspaceActionLaneAction _chainQuickAction({
    required String label,
    required IconData icon,
    required int fallbackTab,
    required String source,
    required AssetChainSummary? chain,
    WorkspaceActionLaneTone tone = WorkspaceActionLaneTone.outline,
  }) {
    return WorkspaceActionLaneAction(
      label: label,
      icon: icon,
      onTap: () {
        if (chain != null) {
          _openChainWorkspace(chain, source: source);
        } else {
          widget.onNavigateToTab(fallbackTab);
        }
      },
      tone: tone,
    );
  }

  void _handleDutyAction(DutyAction action, DashboardSummary summary) {
    switch (action.command) {
      case 'open_audit':
        widget.onNavigateToTab(4);
        return;
      case 'open_workspace':
        final context = buildLaunchContextFromDutyAction(
          action,
          prefix: 'Duty Actions',
        );
        final chain = _chainFor(summary, action.chainKey);
        if (chain != null) {
          final sourceLabel = context.sourceLabel;
          switch (chain.key) {
            case 'dataset':
              final onOpenDataAnalysis = widget.onOpenDataAnalysis;
              if (onOpenDataAnalysis != null) {
                onOpenDataAnalysis(
                  DataAnalysisLaunchIntent.workspace(
                    sourceLabel: sourceLabel,
                    context: context,
                  ),
                );
              } else {
                widget.onNavigateToTab(2);
              }
              return;
            case 'model':
              final onOpenAiLab = widget.onOpenAiLab;
              if (onOpenAiLab != null) {
                onOpenAiLab(
                  AiLabLaunchIntent.deepLearning(
                    '',
                    sourceLabel: sourceLabel,
                    context: context,
                  ),
                );
              } else {
                widget.onNavigateToTab(3);
              }
              return;
            case 'knowledge':
              final onOpenAiLab = widget.onOpenAiLab;
              if (onOpenAiLab != null) {
                onOpenAiLab(
                  AiLabLaunchIntent.rag(
                    '',
                    sourceLabel: sourceLabel,
                    context: context,
                  ),
                );
              } else {
                widget.onNavigateToTab(3);
              }
              return;
            case 'optimization':
              final onOpenOptimization = widget.onOpenOptimization;
              if (onOpenOptimization != null) {
                onOpenOptimization(
                  OptimizationLaunchIntent(
                    sourceLabel: sourceLabel,
                    context: context,
                  ),
                );
              } else {
                widget.onNavigateToTab(1);
              }
              return;
          }
          return;
        }
        switch (action.chainKey) {
          case 'dataset':
            widget.onNavigateToTab(2);
            return;
          case 'model':
          case 'knowledge':
            widget.onNavigateToTab(3);
            return;
          case 'optimization':
            widget.onNavigateToTab(1);
            return;
        }
        return;
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.viewModel,
      builder: (context, _) {
        final summary = widget.viewModel.summary;
        final content = RefreshIndicator(
          onRefresh: widget.viewModel.loadSummary,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              if (widget.surfaceMode.isStandalone)
                SliverAppBar(
                  pinned: true,
                  expandedHeight: 120,
                  backgroundColor: AppColors.surface,
                  foregroundColor: AppColors.textPrimary,
                  flexibleSpace: FlexibleSpaceBar(
                    titlePadding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                    title: Text('Operations Hub', style: AppTextStyles.h3),
                    background: Container(
                      decoration: const BoxDecoration(
                        gradient: AppColors.backgroundGradient,
                      ),
                    ),
                  ),
                ),
              if (!ResponsiveHelper.isDesktop(context) &&
                  summary != null &&
                  widget.surfaceMode.isStandalone)
                SliverToBoxAdapter(
                  child: SystemStatusStrip(items: summary.systemStatus),
                ),
              SliverToBoxAdapter(
                child: ResponsiveWrapper(
                  child: Padding(
                    padding: ResponsiveHelper.getPagePadding(context),
                    child: _buildBody(summary),
                  ),
                ),
              ),
            ],
          ),
        );

        return WorkbenchPageFrame(
          surfaceMode: widget.surfaceMode,
          body: content,
        );
      },
    );
  }

  Widget _buildBody(DashboardSummary? summary) {
    if (widget.viewModel.isLoading && summary == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 120),
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (widget.viewModel.errorMessage != null && summary == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 120),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                widget.viewModel.errorMessage!,
                style: AppTextStyles.bodyMedium,
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: widget.viewModel.loadSummary,
                child: const Text('重试'),
              ),
            ],
          ),
        ),
      );
    }

    final safeSummary = summary;
    if (safeSummary == null) {
      return const SizedBox.shrink();
    }

    final modelStatus = safeSummary.systemStatus
        .cast<SystemStatusItem?>()
        .firstWhere((item) => item?.key == 'model', orElse: () => null);
    final ragStatus = safeSummary.systemStatus
        .cast<SystemStatusItem?>()
        .firstWhere((item) => item?.key == 'rag', orElse: () => null);
    final datasetChain = _chainFor(safeSummary, 'dataset');
    final modelChain = _chainFor(safeSummary, 'model');
    final knowledgeChain = _chainFor(safeSummary, 'knowledge');
    final optimizationChain = _chainFor(safeSummary, 'optimization');
    final focusChain = selectPriorityChain(safeSummary.assetSummary);
    final degradedSystems = safeSummary.systemStatus
        .where((item) => item.status != 'healthy')
        .length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.surfaceMode.isEmbedded) ...[
          EmbeddedPageHeader(
            title: 'Operations Hub',
            description: '统一查看系统状态、最近任务、数据资产和风险提醒。概览页只展示当前最关键的运行信号。',
            badges: [
              EmbeddedHeaderBadge(
                label: '24h 作业',
                value: '${safeSummary.kpis.jobs24h}',
                accent: AppColors.primary,
                icon: Icons.schedule_rounded,
              ),
              EmbeddedHeaderBadge(
                label: '失败任务',
                value: '${safeSummary.kpis.failedJobs}',
                accent: safeSummary.kpis.failedJobs > 0
                    ? AppColors.warning
                    : AppColors.success,
                icon: safeSummary.kpis.failedJobs > 0
                    ? Icons.warning_amber_rounded
                    : Icons.verified_rounded,
              ),
              EmbeddedHeaderBadge(
                label: '模型资产',
                value: '${safeSummary.kpis.modelCount}',
                accent: AppColors.cta,
                icon: Icons.memory_rounded,
              ),
            ],
          ),
          const SizedBox(height: 20),
        ],
        DutyContextBoard(
          title: '工业能源与 AI 驾驶舱',
          description: '把作业密度、资产库存、当前值班链路和系统健康收在同一块控制板里，减少概览页顶部的分散摘要。',
          icon: Icons.space_dashboard_rounded,
          accent: AppColors.primary,
          metrics: [
            DutyMetric(
              label: '数据资产',
              value: '${safeSummary.kpis.datasetCount}',
              color: AppColors.primary,
            ),
            DutyMetric(
              label: '分析记录',
              value: '${safeSummary.kpis.analysisCount}',
              color: AppColors.cta,
            ),
            DutyMetric(
              label: '模型资产',
              value: '${safeSummary.kpis.modelCount}',
              color: AppColors.success,
            ),
            DutyMetric(
              label: '24h 作业',
              value: '${safeSummary.kpis.jobs24h}',
              color: AppColors.primary,
            ),
            DutyMetric(
              label: '失败作业',
              value: '${safeSummary.kpis.failedJobs}',
              color: safeSummary.kpis.failedJobs > 0
                  ? AppColors.error
                  : AppColors.success,
            ),
          ],
          signalStrip: DutySignalStrip(
            summary: safeSummary.dutySummary,
            accent: AppColors.primary,
          ),
          currentWatch: safeSummary.dutySummary.focusWatch.isNotEmpty
              ? safeSummary.dutySummary.focusWatch
              : (focusChain == null
                    ? '当前暂无高优先级资产链路，优先关注系统状态、失败作业和统一事件总线。'
                    : buildChainCurrentWatch(focusChain)),
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
            if (safeSummary.dutySummary.focusOwnerLabel != '--')
              DutyContextFact(
                label: '责任',
                value: safeSummary.dutySummary.focusOwnerLabel,
                icon: Icons.badge_rounded,
              ),
            if (safeSummary.dutySummary.focusEscalationStateLabel != '--')
              DutyContextFact(
                label: '升级',
                value: safeSummary.dutySummary.focusEscalationStateLabel,
                icon: Icons.escalator_warning_rounded,
                foreground: safeSummary.dutySummary.escalatedCount > 0
                    ? AppColors.warning
                    : AppColors.textSecondary,
                background: safeSummary.dutySummary.escalatedCount > 0
                    ? AppColors.warningLight
                    : AppColors.background,
              ),
            DutyContextFact(
              label: '系统',
              value: degradedSystems == 0 ? '健康' : '$degradedSystems 项关注',
              icon: Icons.health_and_safety_rounded,
              foreground: degradedSystems == 0
                  ? AppColors.success
                  : AppColors.warning,
              background: degradedSystems == 0
                  ? AppColors.successLight
                  : AppColors.warningLight,
            ),
            DutyContextFact(
              label: '告警',
              value: '${safeSummary.alerts.length}',
              icon: Icons.notifications_active_rounded,
            ),
          ],
          footerTitle: '值班动作',
          footer: WorkspaceInlineActionBar(
            spacing: 12,
            runSpacing: 12,
            actions: safeSummary.dutySummary.overviewActions.isNotEmpty
                ? safeSummary.dutySummary.overviewActions
                      .map(
                        (action) => WorkspaceActionLaneAction(
                          label: action.label,
                          icon: _dutyActionIcon(action.command, action.chainKey),
                          onTap: () => _handleDutyAction(action, safeSummary),
                          tone: _dutyActionTone(action.tone),
                        ),
                      )
                      .toList(growable: false)
                : [
                    _chainQuickAction(
                      label: '上传并分析数据',
                      icon: Icons.upload_file_rounded,
                      chain: datasetChain,
                      fallbackTab: 2,
                      source: 'Duty Actions',
                      tone: WorkspaceActionLaneTone.primary,
                    ),
                    _chainQuickAction(
                      label: '运行能源优化',
                      icon: Icons.bolt_rounded,
                      chain: optimizationChain,
                      fallbackTab: 1,
                      source: 'Duty Actions',
                      tone: WorkspaceActionLaneTone.tonal,
                    ),
                    _chainQuickAction(
                      label: '开始模型训练',
                      icon: Icons.model_training_rounded,
                      chain: modelChain,
                      fallbackTab: 3,
                      source: 'Duty Actions',
                    ),
                    _chainQuickAction(
                      label: '构建知识库',
                      icon: Icons.auto_awesome_rounded,
                      chain: knowledgeChain,
                      fallbackTab: 3,
                      source: 'Duty Actions',
                    ),
                    WorkspaceActionLaneAction(
                      label: '查看历史与审计',
                      icon: Icons.fact_check_rounded,
                      onTap: () => widget.onNavigateToTab(4),
                    ),
                  ],
          ),
        ),
        const SizedBox(height: 20),
        IncidentPriorityStrip(
          summary: safeSummary.assetSummary,
          dutySummary: safeSummary.dutySummary,
          onOpenChain: (chain) {
            _openChainWorkspace(chain, source: 'Incident Priority Strip');
          },
        ),
        const SizedBox(height: 20),
        IncidentRunbookBoard(
          summary: safeSummary.assetSummary,
          onOpenChain: (chain) {
            _openChainWorkspace(chain, source: 'Runbook Queue');
          },
        ),
        const SizedBox(height: 20),
        DutySectionBlock(
          title: '资产库存',
          subtitle: '统一查看数据、模型、知识库和优化快照的最近版本',
          child: AssetInventoryBoard(
            summary: safeSummary.assetSummary,
            dutySummary: safeSummary.dutySummary,
            alerts: safeSummary.alerts,
            onNavigateToTab: widget.onNavigateToTab,
            onOpenChain: (chain) {
              _openChainWorkspace(chain, source: 'Asset Inventory');
            },
          ),
        ),
        const SizedBox(height: 20),
        DutySectionBlock(
          title: '版本轨迹',
          subtitle: '查看统一资产台账中的最近版本和血缘摘要',
          child: AssetVersionTimelineBoard(
            summary: safeSummary.assetSummary,
            onNavigateToTab: widget.onNavigateToTab,
          ),
        ),
        const SizedBox(height: 20),
        DutySectionBlock(
          title: '运维叙事',
          subtitle: '把版本、最近活动和失败链路按资产链路串成统一处置上下文。',
          child: OperationsNarrativeBoard(
            summary: safeSummary,
            onOpenChain: (chain) {
              _openChainWorkspace(chain, source: 'Operations Narrative');
            },
          ),
        ),
        const SizedBox(height: 20),
        AssetGovernanceQueue(
          items: safeSummary.assetSummary.governance,
          failureChains: safeSummary.assetSummary.failureChains,
          title: '全局处置中心',
          description: '基于统一资产摘要直接给出当前需要优先处理的资产链路。',
          onAction: (item) {
            final chain = _chainFor(safeSummary, item.key);
            if (chain != null) {
              _openChainWorkspace(chain, source: 'Asset Governance Queue');
              return;
            }
            switch (item.key) {
              case 'dataset':
                widget.onNavigateToTab(2);
                return;
              case 'model':
              case 'knowledge':
                widget.onNavigateToTab(3);
                return;
              case 'optimization':
                widget.onNavigateToTab(1);
                return;
            }
          },
          onFailureAction: (chain) {
            final chainSummary = _chainFor(safeSummary, chain.key);
            if (chainSummary != null) {
              _openChainWorkspace(
                chainSummary,
                source: 'Asset Governance Queue',
              );
              return;
            }
            switch (chain.key) {
              case 'dataset':
                widget.onNavigateToTab(2);
                return;
              case 'model':
              case 'knowledge':
                widget.onNavigateToTab(3);
                return;
              case 'optimization':
                widget.onNavigateToTab(1);
                return;
            }
          },
        ),
        const SizedBox(height: 20),
        LayoutBuilder(
          builder: (context, constraints) {
            final stacked = constraints.maxWidth < 1040;
            final left = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DutySectionBlock(
                  title: '统一事件总线',
                  subtitle: '按时间查看链路版本、活跃作业、失败节点和审计动作',
                  child: OperationsEventBusBoard(
                    summary: safeSummary,
                    onOpenChain: (chain) {
                      _openChainWorkspace(chain, source: 'Unified Event Bus');
                    },
                  ),
                ),
                const SizedBox(height: 20),
                DutySectionBlock(
                  title: '最近数据资产',
                  subtitle: '最近完成分析的数据集',
                  child: safeSummary.recentAssets.isEmpty
                      ? const _EmptySection(message: '暂无近期数据资产')
                      : Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: safeSummary.recentAssets
                              .map(
                                (asset) => SizedBox(
                                  width: stacked ? double.infinity : 260,
                                  child: DatasetAssetCard(asset: asset),
                                ),
                              )
                              .toList(growable: false),
                        ),
                  ),
              ],
            );

            final right = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DutySectionBlock(
                  title: '系统提醒',
                  subtitle: '依赖、失败任务与数据空缺',
                  child: safeSummary.alerts.isEmpty
                      ? const _EmptySection(message: '当前无高优先级告警')
                      : Column(
                          children: safeSummary.alerts
                              .map(
                                (alert) => Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: AlertPanel(alert: alert),
                                ),
                              )
                              .toList(growable: false),
                        ),
                  ),
                const SizedBox(height: 20),
                DutySectionBlock(
                  title: '模型与知识状态',
                  subtitle: '核心服务可用性',
                  child: Column(
                    children: [
                      if (modelStatus != null)
                        ModelStatusCard(
                          title: '负载预测模型',
                          status: modelStatus,
                          subtitle: '能源优化和驾驶舱预测依赖该模型。',
                        ),
                      if (modelStatus != null && ragStatus != null)
                        const SizedBox(height: 12),
                      if (ragStatus != null)
                        ModelStatusCard(
                          title: 'RAG 知识服务',
                          status: ragStatus,
                          subtitle: '问答和文档检索依赖知识库构建结果。',
                        ),
                    ],
                  ),
                ),
              ],
            );

            if (stacked) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [left, const SizedBox(height: 20), right],
              );
            }

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(flex: 7, child: left),
                const SizedBox(width: 20),
                Expanded(flex: 5, child: right),
              ],
            );
          },
        ),
      ],
    );
  }

}

WorkspaceActionLaneTone _dutyActionTone(String tone) {
  switch (tone) {
    case 'primary':
      return WorkspaceActionLaneTone.primary;
    case 'tonal':
      return WorkspaceActionLaneTone.tonal;
    default:
      return WorkspaceActionLaneTone.outline;
  }
}

IconData _dutyActionIcon(String command, String chainKey) {
  switch (command) {
    case 'open_audit':
      return Icons.fact_check_rounded;
  }

  switch (chainKey) {
    case 'dataset':
      return Icons.upload_file_rounded;
    case 'model':
      return Icons.model_training_rounded;
    case 'knowledge':
      return Icons.auto_awesome_rounded;
    case 'optimization':
      return Icons.bolt_rounded;
    default:
      return Icons.arrow_outward_rounded;
  }
}

class _EmptySection extends StatelessWidget {
  const _EmptySection({required this.message});

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
      child: Text(message, style: AppTextStyles.bodyMedium),
    );
  }
}
