/// 工业驾驶舱概览页
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/compute_rollout_policy.dart';
import '../models/control_task_record.dart';
import '../models/data_analysis_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../models/optimization_launch_intent.dart';
import '../utils/asset_chain_context.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/approval_queue_view_model.dart';
import '../viewmodels/compute_governance_view_model.dart';
import '../viewmodels/control_task_view_model.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/operation_console_view_model.dart';
import '../widgets/operations/alert_panel.dart';
import '../widgets/operations/approval_queue_board.dart';
import '../widgets/operations/approval_resolution_dialog.dart';
import '../widgets/operations/asset_governance_queue.dart';
import '../widgets/operations/asset_inventory_board.dart';
import '../widgets/operations/asset_version_timeline_board.dart';
import '../widgets/operations/compute_acceleration_board.dart';
import '../widgets/operations/compute_rollout_governance_board.dart';
import '../widgets/operations/control_task_board.dart';
import '../widgets/operations/control_task_edit_dialog.dart';
import '../widgets/operations/control_plane_status_board.dart';
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
import '../widgets/operations/operation_console_board.dart';
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
    this.computeGovernanceViewModel,
    this.controlTaskViewModel,
    this.approvalQueueViewModel,
    this.operationConsoleViewModel,
    this.surfaceMode = WorkbenchSurfaceMode.standalone,
  });

  final DashboardViewModel viewModel;
  final ValueChanged<int> onNavigateToTab;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;
  final ComputeGovernanceViewModel? computeGovernanceViewModel;
  final ControlTaskViewModel? controlTaskViewModel;
  final ApprovalQueueViewModel? approvalQueueViewModel;
  final OperationConsoleViewModel? operationConsoleViewModel;
  final WorkbenchSurfaceMode surfaceMode;

  @override
  State<OperationsHubScreen> createState() => _OperationsHubScreenState();
}

class _OperationsHubScreenState extends State<OperationsHubScreen> {
  String? _highlightedControlTaskId;

  @override
  void initState() {
    super.initState();
    widget.viewModel.initialize();
    widget.computeGovernanceViewModel?.initialize();
    widget.controlTaskViewModel?.initialize();
    widget.approvalQueueViewModel?.initialize();
  }

  void _inspectControlTask(String taskId) {
    setState(() {
      _highlightedControlTaskId = taskId;
    });
  }

  Future<void> _openOperationConsole(
    String operationId, {
    JobRecord? seed,
  }) async {
    final viewModel = widget.operationConsoleViewModel;
    if (viewModel == null) {
      return;
    }
    await viewModel.selectOperation(operationId, seed: seed);
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
            OptimizationLaunchIntent(
              sourceLabel: sourceLabel,
              context: context,
            ),
          );
        } else {
          widget.onNavigateToTab(1);
        }
        break;
      default:
        widget.onNavigateToTab(0);
    }
  }

  Future<void> _runControlTask(ControlTaskRecord task) async {
    final viewModel = widget.controlTaskViewModel;
    if (viewModel == null) {
      return;
    }

    final operation = await viewModel.runControlTask(task);
    if (!mounted) {
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    if (operation == null) {
      final errorMessage = viewModel.errorMessage ?? '触发规划任务失败';
      messenger.showSnackBar(
        SnackBar(content: Text(errorMessage), backgroundColor: AppColors.error),
      );
      return;
    }

    final awaitingApproval = operation.status == 'awaiting_approval';
    await widget.controlTaskViewModel?.loadControlTasks();
    await widget.approvalQueueViewModel?.loadQueue();
    await _openOperationConsole(
      operation.operationId ?? operation.jobId,
      seed: operation,
    );
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          awaitingApproval
              ? '已创建待审批运行: ${task.title}'
              : '已触发规划任务: ${task.title}',
        ),
        backgroundColor: awaitingApproval
            ? AppColors.warning
            : AppColors.success,
      ),
    );
  }

  Future<void> _toggleControlTask(ControlTaskRecord task) async {
    final viewModel = widget.controlTaskViewModel;
    if (viewModel == null) {
      return;
    }

    final updated = await viewModel.setControlTaskEnabled(
      task,
      enabled: !task.enabled,
    );
    if (!mounted) {
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    if (updated == null) {
      final errorMessage = viewModel.errorMessage ?? '更新规划任务状态失败';
      messenger.showSnackBar(
        SnackBar(content: Text(errorMessage), backgroundColor: AppColors.error),
      );
      return;
    }

    messenger.showSnackBar(
      SnackBar(
        content: Text(
          updated.enabled ? '已恢复规划任务: ${task.title}' : '已暂停规划任务: ${task.title}',
        ),
        backgroundColor: updated.enabled
            ? AppColors.success
            : AppColors.warning,
      ),
    );
  }

  Future<void> _setComputeRolloutMode(
    ComputeRolloutComponentPolicy component,
    String rolloutMode,
  ) async {
    final viewModel = widget.computeGovernanceViewModel;
    if (viewModel == null) {
      return;
    }

    final updated = await viewModel.updateRolloutMode(
      component.key,
      rolloutMode: rolloutMode,
    );
    if (!mounted) {
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    if (updated == null) {
      final errorMessage = viewModel.errorMessage ?? '更新计算治理策略失败';
      messenger.showSnackBar(
        SnackBar(content: Text(errorMessage), backgroundColor: AppColors.error),
      );
      return;
    }

    await widget.viewModel.loadSummary();
    messenger.showSnackBar(
      SnackBar(
        content: Text('已更新 ${component.label} 的 rollout 模式'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  Future<void> _toggleControlTaskApproval(ControlTaskRecord task) async {
    final viewModel = widget.controlTaskViewModel;
    if (viewModel == null) {
      return;
    }

    final requiredApproval = task.approvalPolicy['required'] == true;
    final nextPolicy = <String, dynamic>{
      ...task.approvalPolicy,
      'required': !requiredApproval,
      'mode': requiredApproval ? 'auto' : 'manual',
    };

    final updated = await viewModel.setControlTaskApprovalPolicy(
      task,
      approvalPolicy: nextPolicy,
    );
    if (!mounted) {
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    if (updated == null) {
      final errorMessage = viewModel.errorMessage ?? '更新规划任务审批策略失败';
      messenger.showSnackBar(
        SnackBar(content: Text(errorMessage), backgroundColor: AppColors.error),
      );
      return;
    }

    final nextRequired = updated.approvalPolicy['required'] == true;
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          nextRequired ? '已切换为审批执行: ${task.title}' : '已切换为自动执行: ${task.title}',
        ),
        backgroundColor: nextRequired ? AppColors.warning : AppColors.success,
      ),
    );
  }

  Future<void> _editControlTaskDefinition(ControlTaskRecord task) async {
    final viewModel = widget.controlTaskViewModel;
    if (viewModel == null) {
      return;
    }

    final draft = await showControlTaskEditDialog(context, task);
    if (!mounted || draft == null) {
      return;
    }

    final updated = await viewModel.updateControlTaskDefinition(
      task,
      schedule: draft.schedule,
      owner: draft.owner,
      dependencies: draft.dependencies,
      approvalPolicy: draft.approvalPolicy,
      defaultInput: draft.defaultInput,
    );
    if (!mounted) {
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    if (updated == null) {
      final errorMessage = viewModel.errorMessage ?? '更新规划任务定义失败';
      messenger.showSnackBar(
        SnackBar(content: Text(errorMessage), backgroundColor: AppColors.error),
      );
      return;
    }

    messenger.showSnackBar(
      SnackBar(
        content: Text('已更新规划任务定义: ${task.title}'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  Future<void> _resolveApproval(JobRecord job, {required bool approved}) async {
    final viewModel = widget.approvalQueueViewModel;
    if (viewModel == null) {
      return;
    }

    final message = await showApprovalResolutionDialog(
      context,
      approved: approved,
      title: job.displayTitle,
    );
    if (!mounted || message == null) {
      return;
    }

    final updated = await viewModel.resolve(
      job,
      approved: approved,
      message: message.isEmpty ? null : message,
    );
    if (!mounted) {
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    if (updated == null) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(viewModel.errorMessage ?? '审批操作失败'),
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }
    await _openOperationConsole(
      updated.operationId ?? updated.jobId,
      seed: updated,
    );
    await widget.controlTaskViewModel?.loadControlTasks();
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          approved
              ? '已批准任务: ${job.displayTitle}'
              : '已驳回任务: ${job.displayTitle}',
        ),
        backgroundColor: approved ? AppColors.success : AppColors.warning,
      ),
    );
  }

  Future<void> _resolveSelectedOperationApproval({
    required bool approved,
  }) async {
    final viewModel = widget.operationConsoleViewModel;
    final operation = viewModel?.selectedOperation;
    if (viewModel == null || operation == null) {
      return;
    }

    final message = await showApprovalResolutionDialog(
      context,
      approved: approved,
      title: operation.displayTitle,
    );
    if (!mounted || message == null) {
      return;
    }

    final updated = await viewModel.resolveSelectedApproval(
      approved: approved,
      message: message.isEmpty ? null : message,
    );
    if (!mounted) {
      return;
    }
    final messenger = ScaffoldMessenger.of(context);

    if (updated == null) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(viewModel.errorMessage ?? '审批操作失败'),
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }

    await widget.approvalQueueViewModel?.loadQueue();
    await widget.controlTaskViewModel?.loadControlTasks();
    if (!mounted) {
      return;
    }
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          approved
              ? '已批准运行: ${operation.displayTitle}'
              : '已驳回运行: ${operation.displayTitle}',
        ),
        backgroundColor: approved ? AppColors.success : AppColors.warning,
      ),
    );
  }

  Future<void> _retrySelectedOperation() async {
    final viewModel = widget.operationConsoleViewModel;
    final operation = viewModel?.selectedOperation;
    if (viewModel == null || operation == null) {
      return;
    }

    final updated = await viewModel.retrySelected();
    if (!mounted) {
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    if (updated == null) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(viewModel.errorMessage ?? '重试运行失败'),
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }
    await widget.controlTaskViewModel?.loadControlTasks();
    if (!mounted) {
      return;
    }
    messenger.showSnackBar(
      SnackBar(
        content: Text('已重试运行: ${operation.displayTitle}'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  Future<void> _cancelSelectedOperation() async {
    final viewModel = widget.operationConsoleViewModel;
    final operation = viewModel?.selectedOperation;
    if (viewModel == null || operation == null) {
      return;
    }

    final updated = await viewModel.cancelSelected();
    if (!mounted) {
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    if (updated == null) {
      messenger.showSnackBar(
        SnackBar(
          content: Text(viewModel.errorMessage ?? '取消运行失败'),
          backgroundColor: AppColors.error,
        ),
      );
      return;
    }
    await widget.controlTaskViewModel?.loadControlTasks();
    await widget.approvalQueueViewModel?.loadQueue();
    if (!mounted) {
      return;
    }
    messenger.showSnackBar(
      SnackBar(
        content: Text('已取消运行: ${operation.displayTitle}'),
        backgroundColor: AppColors.warning,
      ),
    );
  }

  AssetChainSummary? _chainFor(DashboardSummary summary, String key) {
    return summary.assetSummary.chainSummaries
        .cast<AssetChainSummary?>()
        .firstWhere((chain) => chain?.key == key, orElse: () => null);
  }

  DutyAction _fallbackDutyAction({
    required String chainKey,
    required String label,
    required String tone,
    required AssetChainSummary? chain,
  }) {
    return DutyAction(
      command: 'open_workspace',
      label: label,
      tone: tone,
      chainKey: chainKey,
      chainLabel: chain?.label ?? label,
      workspaceTarget: 'workspace',
      workspaceTargetLabel: '工作台',
      cardTarget: 'summary',
      cardTargetLabel: '当前卡片',
      incidentTarget: 'focus',
      incidentTargetLabel: '当前焦点',
      workspaceBrief: '',
    );
  }

  WorkspaceActionLaneAction _fallbackDutyQuickAction({
    required DashboardSummary summary,
    required String chainKey,
    required String label,
    required IconData icon,
    required int fallbackTab,
    required AssetChainSummary? chain,
    String? semanticKey,
    WorkspaceActionLaneTone tone = WorkspaceActionLaneTone.outline,
  }) {
    final action = _fallbackDutyAction(
      chainKey: chainKey,
      label: label,
      tone: switch (tone) {
        WorkspaceActionLaneTone.primary => 'primary',
        WorkspaceActionLaneTone.tonal => 'tonal',
        WorkspaceActionLaneTone.outline => 'outline',
      },
      chain: chain,
    );
    return WorkspaceActionLaneAction(
      label: label,
      icon: icon,
      semanticKey: semanticKey,
      onTap: () {
        if (chain != null) {
          _handleDutyAction(action, summary);
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
      listenable: Listenable.merge([
        widget.viewModel,
        if (widget.controlTaskViewModel != null) widget.controlTaskViewModel!,
        if (widget.approvalQueueViewModel != null)
          widget.approvalQueueViewModel!,
        if (widget.operationConsoleViewModel != null)
          widget.operationConsoleViewModel!,
      ]),
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
      final errorMessage = widget.viewModel.errorMessage!;
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            DutyContextBoard(
              title: '值班控制板',
              description: '驾驶舱摘要暂时不可用，页面已切换到降级模式。你仍然可以继续进入主工作台排查问题。',
              icon: Icons.warning_amber_rounded,
              accent: AppColors.warning,
              metrics: const [
                DutyMetric(
                  label: 'STATE',
                  value: 'DEGRADED',
                  color: AppColors.warning,
                ),
              ],
              currentWatch: errorMessage,
              contextFacts: const [
                DutyContextFact(
                  label: 'Workspace',
                  value: 'Operations Hub',
                  icon: Icons.space_dashboard_rounded,
                ),
                DutyContextFact(
                  label: 'Mode',
                  value: 'Fallback',
                  icon: Icons.health_and_safety_rounded,
                  foreground: AppColors.warning,
                  background: AppColors.warningLight,
                ),
              ],
              footerTitle: '恢复动作',
              footer: WorkspaceInlineActionBar(
                recommendedActionKey: 'retry_summary',
                actions: [
                  WorkspaceActionLaneAction(
                    label: '重试驾驶舱摘要',
                    icon: Icons.refresh_rounded,
                    onTap: widget.viewModel.loadSummary,
                    semanticKey: 'retry_summary',
                    tone: WorkspaceActionLaneTone.primary,
                  ),
                  WorkspaceActionLaneAction(
                    label: '打开历史与审计',
                    icon: Icons.fact_check_rounded,
                    onTap: () => widget.onNavigateToTab(4),
                    semanticKey: 'open_audit',
                  ),
                  WorkspaceActionLaneAction(
                    label: '打开数据分析工作台',
                    icon: Icons.analytics_rounded,
                    onTap: () => widget.onNavigateToTab(2),
                    semanticKey: 'open_data_analysis',
                    tone: WorkspaceActionLaneTone.tonal,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            AlertPanel(
              alert: DashboardAlert(
                severity: 'warning',
                title: '驾驶舱已进入恢复模式',
                message: '当前无法加载统一摘要，但主工作台和审计入口仍可访问。优先重试摘要，或直接进入具体工作台继续排障。',
              ),
            ),
          ],
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
    final focusChain = selectDutyFocusChain(
      safeSummary.assetSummary,
      safeSummary.dutySummary,
    );
    final degradedSystems = safeSummary.systemStatus
        .where((item) => item.status != 'healthy')
        .length;
    final cardFactValue = buildDutyContextCardValue(
      focusChain?.cardTargetLabel,
    );
    final incidentFactValue = buildDutyContextIncidentValue(
      focusChain?.incidentTargetLabel,
    );
    final orderedSections =
        <MapEntry<String, Widget>>[
          MapEntry(
            'inventory',
            DutySectionBlock(
              title: '资产库存',
              subtitle: '统一查看数据、模型、知识库和优化快照的最近版本',
              trailing:
                  _isDutyFocusSection(
                    'inventory',
                    safeSummary.dutySummary,
                    _operationsSectionFocusOrder,
                  )
                  ? _dutyFocusChip()
                  : null,
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
          ),
          MapEntry(
            'timeline',
            DutySectionBlock(
              title: '版本轨迹',
              subtitle: '查看统一资产台账中的最近版本和血缘摘要',
              trailing:
                  _isDutyFocusSection(
                    'timeline',
                    safeSummary.dutySummary,
                    _operationsSectionFocusOrder,
                  )
                  ? _dutyFocusChip()
                  : null,
              child: AssetVersionTimelineBoard(
                summary: safeSummary.assetSummary,
                dutySummary: safeSummary.dutySummary,
                onNavigateToTab: widget.onNavigateToTab,
                onOpenChain: (chain) {
                  _openChainWorkspace(chain, source: 'Asset Version Timeline');
                },
              ),
            ),
          ),
          MapEntry(
            'narrative',
            DutySectionBlock(
              title: '运维叙事',
              subtitle: '把版本、最近活动和失败链路按资产链路串成统一处置上下文。',
              trailing:
                  _isDutyFocusSection(
                    'narrative',
                    safeSummary.dutySummary,
                    _operationsSectionFocusOrder,
                  )
                  ? _dutyFocusChip()
                  : null,
              child: OperationsNarrativeBoard(
                summary: safeSummary,
                dutySummary: safeSummary.dutySummary,
                onOpenChain: (chain) {
                  _openChainWorkspace(chain, source: 'Operations Narrative');
                },
              ),
            ),
          ),
          MapEntry(
            'governance',
            AssetGovernanceQueue(
              items: safeSummary.assetSummary.governance,
              failureChains: safeSummary.assetSummary.failureChains,
              dutySummary: safeSummary.dutySummary,
              title: '全局处置中心',
              description: '基于统一资产摘要直接给出当前需要优先处理的资产链路。',
              trailing:
                  _isDutyFocusSection(
                    'governance',
                    safeSummary.dutySummary,
                    _operationsSectionFocusOrder,
                  )
                  ? _dutyFocusChip()
                  : null,
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
          ),
          MapEntry(
            'event_bus',
            DutySectionBlock(
              title: '统一事件总线',
              subtitle: '按时间查看链路版本、活跃作业、失败节点和审计动作',
              trailing:
                  _isDutyFocusSection(
                    'event_bus',
                    safeSummary.dutySummary,
                    _operationsSectionFocusOrder,
                  )
                  ? _dutyFocusChip()
                  : null,
              child: OperationsEventBusBoard(
                summary: safeSummary,
                onOpenChain: (chain) {
                  _openChainWorkspace(chain, source: 'Unified Event Bus');
                },
              ),
            ),
          ),
          MapEntry(
            'recent_assets',
            DutySectionBlock(
              title: '最近数据资产',
              subtitle: '最近完成分析的数据集',
              trailing:
                  _isDutyFocusSection(
                    'recent_assets',
                    safeSummary.dutySummary,
                    _operationsSectionFocusOrder,
                  )
                  ? _dutyFocusChip()
                  : null,
              child: safeSummary.recentAssets.isEmpty
                  ? const _EmptySection(message: '暂无近期数据资产')
                  : Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: safeSummary.recentAssets
                          .map(
                            (asset) => SizedBox(
                              width: double.infinity,
                              child: DatasetAssetCard(asset: asset),
                            ),
                          )
                          .toList(growable: false),
                    ),
            ),
          ),
          MapEntry(
            'alerts',
            DutySectionBlock(
              title: '系统提醒',
              subtitle: '依赖、失败任务与数据空缺',
              trailing:
                  _isDutyFocusSection(
                    'alerts',
                    safeSummary.dutySummary,
                    _operationsSectionFocusOrder,
                  )
                  ? _dutyFocusChip()
                  : null,
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
          ),
          MapEntry(
            'service_status',
            DutySectionBlock(
              title: '模型与知识状态',
              subtitle: '核心服务可用性',
              trailing:
                  _isDutyFocusSection(
                    'service_status',
                    safeSummary.dutySummary,
                    _operationsSectionFocusOrder,
                  )
                  ? _dutyFocusChip()
                  : null,
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
          ),
        ]..sort(
          (a, b) => compareSectionKeysByDutyFocus(
            a.key,
            b.key,
            safeSummary.dutySummary,
            _operationsSectionFocusOrder,
          ),
        );

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
            if (cardFactValue != null)
              DutyContextFact(
                label: '卡片',
                value: cardFactValue,
                icon: Icons.dashboard_customize_rounded,
              ),
            if (incidentFactValue != null)
              DutyContextFact(
                label: '值班',
                value: incidentFactValue,
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
            recommendedActionKey: _recommendedDutyActionKey(
              safeSummary.dutySummary,
              safeSummary.dutySummary.overviewActions,
            ),
            actions: safeSummary.dutySummary.overviewActions.isNotEmpty
                ? safeSummary.dutySummary.overviewActions
                      .map(
                        (action) => WorkspaceActionLaneAction(
                          label: action.label,
                          icon: _dutyActionIcon(
                            action.command,
                            action.chainKey,
                          ),
                          semanticKey: '${action.command}:${action.chainKey}',
                          onTap: () => _handleDutyAction(action, safeSummary),
                          tone: _dutyActionTone(action.tone),
                        ),
                      )
                      .toList(growable: false)
                : [
                    _fallbackDutyQuickAction(
                      summary: safeSummary,
                      chainKey: 'dataset',
                      label: '上传并分析数据',
                      icon: Icons.upload_file_rounded,
                      chain: datasetChain,
                      fallbackTab: 2,
                      semanticKey: 'open_workspace:dataset',
                      tone: WorkspaceActionLaneTone.primary,
                    ),
                    _fallbackDutyQuickAction(
                      summary: safeSummary,
                      chainKey: 'optimization',
                      label: '运行能源优化',
                      icon: Icons.bolt_rounded,
                      chain: optimizationChain,
                      fallbackTab: 1,
                      semanticKey: 'open_workspace:optimization',
                      tone: WorkspaceActionLaneTone.tonal,
                    ),
                    _fallbackDutyQuickAction(
                      summary: safeSummary,
                      chainKey: 'model',
                      label: '开始模型训练',
                      icon: Icons.model_training_rounded,
                      chain: modelChain,
                      fallbackTab: 3,
                      semanticKey: 'open_workspace:model',
                    ),
                    _fallbackDutyQuickAction(
                      summary: safeSummary,
                      chainKey: 'knowledge',
                      label: '构建知识库',
                      icon: Icons.auto_awesome_rounded,
                      chain: knowledgeChain,
                      fallbackTab: 3,
                      semanticKey: 'open_workspace:knowledge',
                    ),
                    WorkspaceActionLaneAction(
                      label: '查看历史与审计',
                      icon: Icons.fact_check_rounded,
                      semanticKey: 'open_audit:',
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
            _openChainWorkspace(chain, source: '优先值班链路');
          },
        ),
        const SizedBox(height: 20),
        IncidentRunbookBoard(
          summary: safeSummary.assetSummary,
          dutySummary: safeSummary.dutySummary,
          trailing:
              _isDutyFocusSection(
                'runbook',
                safeSummary.dutySummary,
                _operationsSectionFocusOrder,
              )
              ? _dutyFocusChip()
              : null,
          onOpenChain: (chain) {
            _openChainWorkspace(chain, source: '处置清单');
          },
        ),
        if (safeSummary.controlPlane.enabled || safeSummary.controlPlane.message.isNotEmpty) ...[
          const SizedBox(height: 20),
          ControlPlaneStatusBoard(status: safeSummary.controlPlane),
        ],
        if (safeSummary.computeAcceleration.enabled ||
            safeSummary.computeAcceleration.components.isNotEmpty ||
            safeSummary.computeAcceleration.message.isNotEmpty) ...[
          const SizedBox(height: 20),
          ComputeAccelerationBoard(status: safeSummary.computeAcceleration),
        ],
        if (widget.computeGovernanceViewModel != null) ...[
          const SizedBox(height: 20),
          ComputeRolloutGovernanceBoard(
            policy: widget.computeGovernanceViewModel!.policy.components.isEmpty
                ? safeSummary.computeAcceleration.rollout
                : widget.computeGovernanceViewModel!.policy,
            isLoading: widget.computeGovernanceViewModel!.isLoading,
            isUpdatingComponent:
                widget.computeGovernanceViewModel!.isUpdatingComponent,
            onSetRolloutMode: _setComputeRolloutMode,
          ),
        ],
        if (widget.controlTaskViewModel != null) ...[
          const SizedBox(height: 20),
          ControlTaskBoard(
            tasks: widget.controlTaskViewModel!.tasks,
            isLoading: widget.controlTaskViewModel!.isLoading,
            errorMessage: widget.controlTaskViewModel!.errorMessage,
            onRetry: () => widget.controlTaskViewModel!.loadControlTasks(),
            onRunTask: _runControlTask,
            isTaskRunning: widget.controlTaskViewModel!.isRunningTask,
            onToggleTask: _toggleControlTask,
            isTaskUpdating: widget.controlTaskViewModel!.isUpdatingTask,
            onToggleApproval: _toggleControlTaskApproval,
            onEditDefinition: _editControlTaskDefinition,
            onInspectTaskId: _inspectControlTask,
            highlightedTaskId: _highlightedControlTaskId,
            onOpenLatestOperation: (operation) =>
                _openOperationConsole(operation.operationId),
          ),
        ],
        if (widget.approvalQueueViewModel != null) ...[
          const SizedBox(height: 20),
          ApprovalQueueBoard(
            jobs: widget.approvalQueueViewModel!.jobs,
            isLoading: widget.approvalQueueViewModel!.isLoading,
            errorMessage: widget.approvalQueueViewModel!.errorMessage,
            onRefresh: () => widget.approvalQueueViewModel!.loadQueue(),
            onApprove: (job) => _resolveApproval(job, approved: true),
            onReject: (job) => _resolveApproval(job, approved: false),
            isUpdating: widget.approvalQueueViewModel!.isUpdating,
            onOpenDetails: (job) =>
                _openOperationConsole(job.operationId ?? job.jobId, seed: job),
          ),
        ],
        if (widget.operationConsoleViewModel != null) ...[
          const SizedBox(height: 20),
          OperationConsoleBoard(
            viewModel: widget.operationConsoleViewModel!,
            onApprove: () => _resolveSelectedOperationApproval(approved: true),
            onReject: () => _resolveSelectedOperationApproval(approved: false),
            onRetry: _retrySelectedOperation,
            onCancel: _cancelSelectedOperation,
          ),
        ],
        const SizedBox(height: 20),
        LayoutBuilder(
          builder: (context, constraints) {
            final stacked = constraints.maxWidth < 1040;
            if (stacked) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (var i = 0; i < orderedSections.length; i++) ...[
                    orderedSections[i].value,
                    if (i < orderedSections.length - 1)
                      const SizedBox(height: 20),
                  ],
                ],
              );
            }

            final leftSections = <Widget>[];
            final rightSections = <Widget>[];
            for (var i = 0; i < orderedSections.length; i++) {
              final target = i.isEven ? leftSections : rightSections;
              target.add(orderedSections[i].value);
              if (i + 2 < orderedSections.length) {
                target.add(const SizedBox(height: 20));
              }
            }

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 7,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: leftSections,
                  ),
                ),
                const SizedBox(width: 20),
                Expanded(
                  flex: 5,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: rightSections,
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

const Map<String, List<String>> _operationsSectionFocusOrder = {
  'data_governance': [
    'inventory',
    'recent_assets',
    'governance',
    'event_bus',
    'timeline',
    'narrative',
    'alerts',
    'service_status',
  ],
  'data_handoff': [
    'inventory',
    'recent_assets',
    'event_bus',
    'governance',
    'timeline',
    'narrative',
    'alerts',
    'service_status',
  ],
  'ai_runtime': [
    'governance',
    'event_bus',
    'narrative',
    'service_status',
    'inventory',
    'timeline',
    'alerts',
    'recent_assets',
  ],
  'ai_assets': [
    'inventory',
    'timeline',
    'governance',
    'event_bus',
    'narrative',
    'service_status',
    'alerts',
    'recent_assets',
  ],
  'optimization_operations': [
    'narrative',
    'event_bus',
    'governance',
    'inventory',
    'timeline',
    'alerts',
    'service_status',
    'recent_assets',
  ],
  'optimization_registry': [
    'timeline',
    'inventory',
    'governance',
    'narrative',
    'event_bus',
    'recent_assets',
    'alerts',
    'service_status',
  ],
  'audit_center': [
    'event_bus',
    'governance',
    'narrative',
    'inventory',
    'timeline',
    'alerts',
    'service_status',
    'recent_assets',
  ],
};

bool _isDutyFocusSection(
  String key,
  DutySummary? summary,
  Map<String, List<String>> focusOrder,
) {
  return isDutyFocusSection(key, summary, focusOrder);
}

Widget _dutyFocusChip() {
  return const WorkspaceStatusChip(
    label: '值班焦点',
    icon: Icons.center_focus_strong_rounded,
    foreground: AppColors.primary,
    background: AppColors.infoLight,
  );
}

String? _recommendedDutyActionKey(
  DutySummary? summary,
  List<DutyAction> actions,
) {
  final focusKey = summary?.focusChainKey;
  if (focusKey != null && focusKey.isNotEmpty) {
    for (final action in actions) {
      if (action.command == 'open_workspace' && action.chainKey == focusKey) {
        return '${action.command}:${action.chainKey}';
      }
    }
  }
  for (final action in actions) {
    if (action.command == 'open_workspace') {
      return '${action.command}:${action.chainKey}';
    }
  }
  for (final action in actions) {
    if (action.command == 'open_audit') {
      return '${action.command}:${action.chainKey}';
    }
  }
  return null;
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
