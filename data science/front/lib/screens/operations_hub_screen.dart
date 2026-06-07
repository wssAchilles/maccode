/// 工业驾驶舱概览页
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/ai_lab_launch_intent.dart';
import '../models/compute_governance_activity_entry.dart';
import '../models/compute_rollout_policy.dart';
import '../models/control_task_record.dart';
import '../models/data_analysis_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../models/main_shell_projection.dart';
import '../models/optimization_launch_intent.dart';
import '../models/shell_action_outcome.dart';
import '../utils/asset_chain_context.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/approval_queue_view_model.dart';
import '../viewmodels/compute_governance_view_model.dart';
import '../viewmodels/control_task_view_model.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../viewmodels/main_shell_runtime_view_model.dart';
import '../viewmodels/operation_console_view_model.dart';
import '../viewmodels/operations_hub_coordinator.dart';
import '../widgets/navigation/main_shell_runtime_scope.dart';
import '../widgets/operations/alert_panel.dart';
import '../widgets/operations/approval_queue_board.dart';
import '../widgets/operations/approval_resolution_dialog.dart';
import '../widgets/operations/asset_governance_queue.dart';
import '../widgets/operations/asset_inventory_board.dart';
import '../widgets/operations/asset_version_timeline_board.dart';
import '../widgets/operations/compute_acceleration_board.dart';
import '../widgets/operations/compute_governance_activity_board.dart';
import '../widgets/operations/compute_rollout_change_dialog.dart';
import '../widgets/operations/compute_rollout_governance_board.dart';
import '../widgets/operations/control_task_board.dart';
import '../widgets/operations/control_task_edit_dialog.dart';
import '../widgets/operations/control_plane_status_board.dart';
import '../widgets/operations/dataset_asset_card.dart';
import '../widgets/operations/duty_context_board.dart';
import '../widgets/operations/duty_section_block.dart';
import '../widgets/operations/decision_layout.dart';
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
    this.shellProjection,
    this.isActive = true,
    this.sharedRuntimeManaged = false,
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
  final MainShellProjection? shellProjection;
  final bool isActive;
  final bool sharedRuntimeManaged;
  final WorkbenchSurfaceMode surfaceMode;

  @override
  State<OperationsHubScreen> createState() => _OperationsHubScreenState();
}

class _OperationsHubScreenState extends State<OperationsHubScreen> {
  String? _highlightedControlTaskId;
  String? _lastGovernanceSyncedOperationId;
  bool _deferredSectionsReady = false;
  bool _didActivateWorkspace = false;
  late final OperationsHubCoordinator _coordinator;

  MainShellRuntimeViewModel? get _runtime => widget.sharedRuntimeManaged
      ? MainShellRuntimeScope.maybeOf(context)
      : null;
  Timer? _deferredSectionsTimer;

  @override
  void initState() {
    super.initState();
    _coordinator = OperationsHubCoordinator(
      navigateToTab: widget.onNavigateToTab,
      openAiLab: widget.onOpenAiLab,
      openDataAnalysis: widget.onOpenDataAnalysis,
      openOptimization: widget.onOpenOptimization,
    );
    widget.operationConsoleViewModel?.addListener(
      _handleOperationConsoleUpdate,
    );
    _handleWorkspaceActivation(widget.isActive);
  }

  @override
  void didUpdateWidget(covariant OperationsHubScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.operationConsoleViewModel !=
        widget.operationConsoleViewModel) {
      oldWidget.operationConsoleViewModel?.removeListener(
        _handleOperationConsoleUpdate,
      );
      widget.operationConsoleViewModel?.addListener(
        _handleOperationConsoleUpdate,
      );
    }
    if (oldWidget.isActive != widget.isActive) {
      _handleWorkspaceActivation(widget.isActive);
    }
  }

  @override
  void dispose() {
    _deferredSectionsTimer?.cancel();
    widget.operationConsoleViewModel?.removeListener(
      _handleOperationConsoleUpdate,
    );
    super.dispose();
  }

  void _handleWorkspaceActivation(bool isActive) {
    if (!widget.sharedRuntimeManaged) {
      widget.operationConsoleViewModel?.setWorkspaceActive(isActive);
    }
    if (!isActive) {
      _deferredSectionsTimer?.cancel();
      _deferredSectionsTimer = null;
      return;
    }
    if (!_didActivateWorkspace) {
      _didActivateWorkspace = true;
      if (!widget.sharedRuntimeManaged) {
        widget.viewModel.initialize();
        widget.computeGovernanceViewModel?.initialize();
        widget.controlTaskViewModel?.initialize();
        widget.approvalQueueViewModel?.initialize();
      }
    }
    _scheduleDeferredSections();
  }

  void _scheduleDeferredSections() {
    if (_deferredSectionsReady || _deferredSectionsTimer != null) {
      return;
    }
    _deferredSectionsTimer = Timer(const Duration(milliseconds: 220), () {
      _deferredSectionsTimer = null;
      if (!mounted || !widget.isActive) {
        return;
      }
      setState(() {
        _deferredSectionsReady = true;
      });
    });
  }

  void _handleOperationConsoleUpdate() {
    unawaited(_syncGovernanceAfterOperation());
  }

  Future<void> _syncGovernanceAfterOperation() async {
    final operation = widget.operationConsoleViewModel?.selectedOperation;
    if (operation == null ||
        (operation.type != 'compute_rollout_change' &&
            operation.type != 'compute_benchmark')) {
      return;
    }
    final operationId = operation.operationId ?? operation.jobId;
    if (!operation.isTerminal ||
        _lastGovernanceSyncedOperationId == operationId) {
      return;
    }
    _lastGovernanceSyncedOperationId = operationId;
    final runtime = _runtime;
    if (runtime != null) {
      await runtime.refreshSharedSnapshot(force: true);
      return;
    }
    await widget.computeGovernanceViewModel?.loadPolicy();
    await widget.viewModel.loadSummary();
    await widget.approvalQueueViewModel?.loadQueue();
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
    final runtime = _runtime;
    if (runtime != null) {
      await runtime.openOperation(operationId, seed: seed);
      return;
    }
    final viewModel = widget.operationConsoleViewModel;
    if (viewModel == null) {
      return;
    }
    await viewModel.selectOperation(operationId, seed: seed);
  }

  void _showActionOutcome(ShellActionOutcome outcome) {
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(
      SnackBar(
        content: Text(outcome.message),
        backgroundColor: _colorForActionTone(outcome.tone),
      ),
    );
  }

  Color _colorForActionTone(ShellActionTone tone) {
    return switch (tone) {
      ShellActionTone.success => AppColors.success,
      ShellActionTone.warning => AppColors.warning,
      ShellActionTone.error => AppColors.error,
      ShellActionTone.info => AppColors.primary,
    };
  }

  void _openChainWorkspace(AssetChainSummary chain, {required String source}) {
    _coordinator.openChainWorkspace(chain, source: source);
  }

  Future<void> _runControlTask(ControlTaskRecord task) async {
    final runtime = _runtime;
    if (runtime != null) {
      final outcome = await runtime.runControlTask(task);
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

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
    await _refreshSharedProjection();
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
    final runtime = _runtime;
    if (runtime != null) {
      final outcome = await runtime.setControlTaskEnabled(
        task,
        enabled: !task.enabled,
      );
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

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

  Future<void> _requestComputeRolloutModeChange(
    ComputeRolloutComponentPolicy component,
    String rolloutMode,
  ) async {
    final runtime = _runtime;
    final viewModel = widget.computeGovernanceViewModel;
    if (viewModel == null && runtime == null) {
      return;
    }

    final draft = await showComputeRolloutChangeDialog(
      context,
      component: component,
      targetRolloutMode: rolloutMode,
    );
    if (!mounted || draft == null) {
      return;
    }

    if (runtime != null) {
      final outcome = await runtime.requestComputeRolloutModeChange(
        component,
        targetPolicy: draft.targetPolicy,
        changeReason: draft.changeReason,
        requestKind: draft.requestKind,
      );
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

    final operation = await viewModel!.requestRolloutModeChange(
      component.key,
      targetPolicy: draft.targetPolicy,
      changeReason: draft.changeReason,
      requestKind: draft.requestKind,
    );
    if (!mounted) {
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    if (operation == null) {
      final errorMessage = viewModel.errorMessage ?? '提交计算治理变更失败';
      messenger.showSnackBar(
        SnackBar(content: Text(errorMessage), backgroundColor: AppColors.error),
      );
      return;
    }

    await _refreshSharedProjection();
    await _openOperationConsole(
      operation.operationId ?? operation.jobId,
      seed: operation,
    );
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          operation.isAwaitingApproval
              ? '已提交 ${component.label} 的治理变更，等待审批'
              : '已提交 ${component.label} 的治理运行',
        ),
        backgroundColor: operation.isAwaitingApproval
            ? AppColors.warning
            : AppColors.success,
      ),
    );
  }

  Future<void> _runComputeBenchmark(
    ComputeRolloutComponentPolicy component,
  ) async {
    final runtime = _runtime;
    if (runtime != null) {
      final outcome = await runtime.requestComputeBenchmark(component);
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

    final viewModel = widget.computeGovernanceViewModel;
    if (viewModel == null) {
      return;
    }

    final operation = await viewModel.requestBenchmark(component.key);
    if (!mounted) {
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    if (operation == null) {
      final errorMessage = viewModel.errorMessage ?? '提交 benchmark 失败';
      messenger.showSnackBar(
        SnackBar(content: Text(errorMessage), backgroundColor: AppColors.error),
      );
      return;
    }

    await _openOperationConsole(
      operation.operationId ?? operation.jobId,
      seed: operation,
    );
    messenger.showSnackBar(
      SnackBar(
        content: Text('已提交 ${component.label} 的 benchmark 运行'),
        backgroundColor: AppColors.success,
      ),
    );
  }

  Future<void> _openComputeGovernanceActivity(
    ComputeGovernanceActivityEntry entry,
  ) async {
    if (!entry.hasLinkedOperation) {
      return;
    }
    await _openOperationConsole(entry.operationId);
  }

  Future<void> _toggleControlTaskApproval(ControlTaskRecord task) async {
    final runtime = _runtime;
    final viewModel = widget.controlTaskViewModel;
    if (viewModel == null && runtime == null) {
      return;
    }

    final requiredApproval = task.approvalPolicy['required'] == true;
    final nextPolicy = <String, dynamic>{
      ...task.approvalPolicy,
      'required': !requiredApproval,
      'mode': requiredApproval ? 'auto' : 'manual',
    };

    if (runtime != null) {
      final outcome = await runtime.setControlTaskApprovalPolicy(
        task,
        approvalPolicy: nextPolicy,
      );
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

    final updated = await viewModel!.setControlTaskApprovalPolicy(
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
    final runtime = _runtime;
    final viewModel = widget.controlTaskViewModel;
    if (viewModel == null && runtime == null) {
      return;
    }

    final draft = await showControlTaskEditDialog(context, task);
    if (!mounted || draft == null) {
      return;
    }

    if (runtime != null) {
      final outcome = await runtime.updateControlTaskDefinition(
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
      _showActionOutcome(outcome);
      return;
    }

    final updated = await viewModel!.updateControlTaskDefinition(
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
    final runtime = _runtime;
    final viewModel = widget.approvalQueueViewModel;
    if (viewModel == null && runtime == null) {
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

    if (runtime != null) {
      final outcome = await runtime.resolveQueuedApprovalAction(
        job,
        approved: approved,
        message: message.isEmpty ? null : message,
      );
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

    final updated = await viewModel!.resolve(
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
    final runtime = _runtime;
    final viewModel = widget.operationConsoleViewModel;
    final operation = viewModel?.selectedOperation;
    if ((viewModel == null && runtime == null) || operation == null) {
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

    if (runtime != null) {
      final outcome = await runtime.resolveSelectedOperationApprovalAction(
        approved: approved,
        message: message.isEmpty ? null : message,
      );
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

    final updated = await viewModel!.resolveSelectedApproval(
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
    final runtime = _runtime;
    final viewModel = widget.operationConsoleViewModel;
    final operation = viewModel?.selectedOperation;
    if ((viewModel == null && runtime == null) || operation == null) {
      return;
    }

    if (runtime != null) {
      final outcome = await runtime.retrySelectedOperationAction();
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

    final updated = await viewModel!.retrySelected();
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
    final runtime = _runtime;
    final viewModel = widget.operationConsoleViewModel;
    final operation = viewModel?.selectedOperation;
    if ((viewModel == null && runtime == null) || operation == null) {
      return;
    }

    if (runtime != null) {
      final outcome = await runtime.cancelSelectedOperationAction();
      if (!mounted) {
        return;
      }
      _showActionOutcome(outcome);
      return;
    }

    final updated = await viewModel!.cancelSelected();
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

  Future<void> _refreshSharedProjection() async {
    final runtime = _runtime;
    if (runtime != null) {
      await runtime.refreshSharedSnapshot(force: true);
      return;
    }
    await Future.wait([
      widget.viewModel.loadSummary(),
      widget.computeGovernanceViewModel?.loadPolicy() ?? Future<void>.value(),
      widget.controlTaskViewModel?.loadControlTasks() ?? Future<void>.value(),
      widget.approvalQueueViewModel?.loadQueue() ?? Future<void>.value(),
    ]);
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

  DashboardSummary? get _summary => widget.sharedRuntimeManaged
      ? (widget.shellProjection?.summary ?? widget.viewModel.summary)
      : widget.viewModel.summary;

  List<ControlTaskRecord> get _controlTasks => widget.sharedRuntimeManaged
      ? (widget.shellProjection?.controlTasks ??
            widget.controlTaskViewModel?.tasks ??
            const <ControlTaskRecord>[])
      : (widget.controlTaskViewModel?.tasks ?? const <ControlTaskRecord>[]);

  List<JobRecord> get _approvalJobs => widget.sharedRuntimeManaged
      ? (widget.shellProjection?.pendingApprovalJobs ??
            widget.approvalQueueViewModel?.jobs ??
            const <JobRecord>[])
      : (widget.approvalQueueViewModel?.jobs ?? const <JobRecord>[]);

  ComputeRolloutPolicy get _computePolicy {
    if (widget.sharedRuntimeManaged && widget.shellProjection != null) {
      return widget.shellProjection!.computePolicy;
    }
    return widget.computeGovernanceViewModel?.policy ??
        const ComputeRolloutPolicy.empty();
  }

  List<ComputeGovernanceActivityEntry> get _computeActivity =>
      widget.sharedRuntimeManaged
      ? (widget.shellProjection?.computeActivity ??
            widget.computeGovernanceViewModel?.recentActivity ??
            const <ComputeGovernanceActivityEntry>[])
      : (widget.computeGovernanceViewModel?.recentActivity ??
            const <ComputeGovernanceActivityEntry>[]);

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([
        widget.viewModel,
        if (widget.computeGovernanceViewModel != null)
          widget.computeGovernanceViewModel!,
        if (widget.controlTaskViewModel != null) widget.controlTaskViewModel!,
        if (widget.approvalQueueViewModel != null)
          widget.approvalQueueViewModel!,
        if (widget.operationConsoleViewModel != null)
          widget.operationConsoleViewModel!,
      ]),
      builder: (context, _) {
        final summary = _summary;
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
    final focusChain = selectDutyFocusChain(
      safeSummary.assetSummary,
      safeSummary.dutySummary,
    );
    final degradedSystems = safeSummary.systemStatus
        .where((item) => item.status != 'healthy')
        .length;
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

    final primaryBanner = safeSummary.alerts.isNotEmpty
        ? DecisionBanner(
            title: safeSummary.alerts.first.title,
            message: safeSummary.alerts.first.message,
            accent: safeSummary.alerts.first.severity == 'error'
                ? AppColors.error
                : AppColors.warning,
            icon: safeSummary.alerts.first.severity == 'error'
                ? Icons.error_outline_rounded
                : Icons.warning_amber_rounded,
          )
        : DecisionBanner(
            title: degradedSystems == 0 ? '运行稳定' : '仍有待处理风险',
            message: safeSummary.dutySummary.focusWatch.isNotEmpty
                ? safeSummary.dutySummary.focusWatch
                : (focusChain == null
                      ? '当前没有新的高优先级链路，建议查看最近关键链路和失败作业。'
                      : buildChainCurrentWatch(focusChain)),
            accent: degradedSystems == 0
                ? AppColors.success
                : AppColors.warning,
            icon: degradedSystems == 0
                ? Icons.verified_rounded
                : Icons.priority_high_rounded,
          );
    final overviewActions = safeSummary.dutySummary.overviewActions;
    final primaryAction = overviewActions.isNotEmpty
        ? DecisionHeaderAction(
            label: overviewActions.first.label,
            icon: _dutyActionIcon(
              overviewActions.first.command,
              overviewActions.first.chainKey,
            ),
            onTap: () => _handleDutyAction(overviewActions.first, safeSummary),
            isPrimary: true,
          )
        : DecisionHeaderAction(
            label: '查看当前风险',
            icon: focusChain == null
                ? Icons.fact_check_rounded
                : _dutyActionIcon('open_workspace', focusChain.key),
            onTap: () {
              if (focusChain != null) {
                _openChainWorkspace(focusChain, source: 'Overview Hero');
                return;
              }
              widget.onNavigateToTab(4);
            },
            isPrimary: true,
          );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DecisionHeaderCard(
          title: '今日运营概览',
          summary: '先看状态、锁定风险，再进入唯一需要处理的工作台。',
          metrics: [
            DecisionHeaderMetric(
              label: '核心作业',
              value: '${safeSummary.kpis.jobs24h}',
              helper: '过去 24 小时',
              accent: AppColors.primary,
              icon: Icons.schedule_rounded,
            ),
            DecisionHeaderMetric(
              label: '当前风险',
              value: degradedSystems == 0 ? '稳定' : '$degradedSystems 项需要关注',
              helper: '系统与资产链路',
              accent: degradedSystems == 0
                  ? AppColors.success
                  : AppColors.warning,
              icon: Icons.health_and_safety_rounded,
            ),
            DecisionHeaderMetric(
              label: '失败任务',
              value: '${safeSummary.kpis.failedJobs}',
              helper: '优先处理失败与超时',
              accent: safeSummary.kpis.failedJobs > 0
                  ? AppColors.error
                  : AppColors.success,
              icon: Icons.warning_amber_rounded,
            ),
            DecisionHeaderMetric(
              label: '关键资产',
              value:
                  '${safeSummary.kpis.datasetCount + safeSummary.kpis.analysisCount + safeSummary.kpis.modelCount}',
              helper: '数据、分析与模型',
              accent: AppColors.cta,
              icon: Icons.inventory_2_rounded,
            ),
          ],
          primaryAction: primaryAction,
          banner: primaryBanner,
        ),
        const SizedBox(height: 20),
        PrimaryWorkflowPanel(
          eyebrow: '业务决策视角',
          title: '当前风险与推荐动作',
          summary: '首屏只保留当前风险、推荐动作和最近关键链路，其他运营面板全部下沉。',
          child: LayoutBuilder(
            builder: (context, constraints) {
              final stacked = constraints.maxWidth < 1040;
              final nextStepLabel = overviewActions.isNotEmpty
                  ? overviewActions.first.label
                  : focusChain == null
                  ? '查看历史与审计'
                  : '进入${focusChain.workspaceTargetLabel}';
              final nextStepImpact =
                  focusChain?.workspaceBrief ??
                  (degradedSystems == 0 ? '当前没有阻塞链路' : '优先处理失败任务和风险资产');
              final nextStepOwner =
                  focusChain?.label ??
                  (overviewActions.isNotEmpty ? '当前主流程' : '历史与审计');
              final failureChains = safeSummary.assetSummary.failureChains
                  .take(3)
                  .toList(growable: false);

              Widget buildRiskColumn() {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _OverviewInsightCard(
                      title: '当前风险',
                      subtitle: primaryBanner.title,
                      accent: safeSummary.alerts.isNotEmpty
                          ? (safeSummary.alerts.first.severity == 'error'
                                ? AppColors.error
                                : AppColors.warning)
                          : (degradedSystems == 0
                                ? AppColors.success
                                : AppColors.warning),
                      body: safeSummary.dutySummary.focusWatch.isNotEmpty
                          ? safeSummary.dutySummary.focusWatch
                          : (focusChain?.workspaceBrief ??
                                '优先处理失败作业、升级项和最新异常链路。'),
                    ),
                    const SizedBox(height: 16),
                    _OverviewInsightCard(
                      title: '推荐动作',
                      subtitle: '首屏只保留一个主动作，其余入口下沉到详情区。',
                      accent: AppColors.primary,
                      body:
                          '下一步：$nextStepLabel\n影响：$nextStepImpact\n责任对象：$nextStepOwner',
                      bodyChild: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '请先完成头部主动作，再进入对应工作台继续处理。',
                            style: AppTextStyles.bodySmall.copyWith(
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                );
              }

              Widget buildChainColumn() {
                return _OverviewInsightCard(
                  title: '最近关键链路',
                  subtitle: '只展示最值得打开的链路，不再把所有运行板块堆在首屏。',
                  accent: AppColors.cta,
                  body: '',
                  bodyChild: failureChains.isEmpty
                      ? Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              focusChain == null
                                  ? '当前没有失败链路，建议转到历史与审计查看最近记录。'
                                  : focusChain.workspaceBrief,
                              style: AppTextStyles.bodyMedium.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                            if (focusChain != null) ...[
                              const SizedBox(height: 12),
                              OutlinedButton.icon(
                                onPressed: () => _openChainWorkspace(
                                  focusChain,
                                  source: 'Recent Key Chain',
                                ),
                                icon: Icon(
                                  _dutyActionIcon(
                                    'open_workspace',
                                    focusChain.key,
                                  ),
                                ),
                                label: Text(
                                  '进入${focusChain.workspaceTargetLabel}',
                                ),
                              ),
                            ],
                          ],
                        )
                      : Column(
                          children: failureChains
                              .map(
                                (chain) => Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: _OverviewChainCard(
                                    title: chain.label,
                                    subtitle:
                                        '${chain.contextLabel} · ${chain.latestPhase}',
                                    description: chain.errorMessage.isNotEmpty
                                        ? chain.errorMessage
                                        : chain.statusMessage,
                                    actionLabel: chain.actionLabel,
                                    actionIcon: _dutyActionIcon(
                                      'open_workspace',
                                      chain.key,
                                    ),
                                    onTap: () => _openOverviewChainByKey(
                                      safeSummary,
                                      chain.key,
                                      source: 'Recent Key Chain',
                                    ),
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
                    buildRiskColumn(),
                    const SizedBox(height: 16),
                    buildChainColumn(),
                  ],
                );
              }

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 6, child: buildRiskColumn()),
                  const SizedBox(width: 16),
                  Expanded(flex: 5, child: buildChainColumn()),
                ],
              );
            },
          ),
        ),
        const SizedBox(height: 20),
        ProgressiveDetailSection(
          title: '运营详情',
          summary: '值班链路、资产台账、事件流和系统提醒保留在这里，需要时再展开。',
          icon: Icons.dashboard_customize_rounded,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
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
              const SizedBox(height: 20),
              _deferredSectionsReady
                  ? LayoutBuilder(
                      builder: (context, constraints) {
                        final stacked = constraints.maxWidth < 1040;
                        if (stacked) {
                          return Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              for (
                                var i = 0;
                                i < orderedSections.length;
                                i++
                              ) ...[
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
                          final target = i.isEven
                              ? leftSections
                              : rightSections;
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
                    )
                  : const _DeferredSectionsPlaceholder(),
            ],
          ),
        ),
        if (safeSummary.controlPlane.enabled ||
            safeSummary.controlPlane.message.isNotEmpty ||
            safeSummary.computeAcceleration.enabled ||
            safeSummary.computeAcceleration.components.isNotEmpty ||
            safeSummary.computeAcceleration.message.isNotEmpty ||
            widget.computeGovernanceViewModel != null) ...[
          const SizedBox(height: 20),
          ProgressiveDetailSection(
            title: '控制面与计算治理',
            summary: '控制面状态、加速配置和基准治理下沉到这里，不再占首屏。',
            icon: Icons.tune_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (safeSummary.controlPlane.enabled ||
                    safeSummary.controlPlane.message.isNotEmpty)
                  ControlPlaneStatusBoard(status: safeSummary.controlPlane),
                if (safeSummary.computeAcceleration.enabled ||
                    safeSummary.computeAcceleration.components.isNotEmpty ||
                    safeSummary.computeAcceleration.message.isNotEmpty) ...[
                  if (safeSummary.controlPlane.enabled ||
                      safeSummary.controlPlane.message.isNotEmpty)
                    const SizedBox(height: 20),
                  ComputeAccelerationBoard(
                    status: safeSummary.computeAcceleration,
                  ),
                ],
                if (widget.computeGovernanceViewModel != null) ...[
                  if (safeSummary.controlPlane.enabled ||
                      safeSummary.controlPlane.message.isNotEmpty ||
                      safeSummary.computeAcceleration.enabled ||
                      safeSummary.computeAcceleration.components.isNotEmpty ||
                      safeSummary.computeAcceleration.message.isNotEmpty)
                    const SizedBox(height: 20),
                  ComputeRolloutGovernanceBoard(
                    policy: _computePolicy.components.isEmpty
                        ? safeSummary.computeAcceleration.rollout
                        : _computePolicy,
                    isLoading: widget.computeGovernanceViewModel!.isLoading,
                    isUpdatingComponent:
                        widget.computeGovernanceViewModel!.isUpdatingComponent,
                    onRequestRolloutMode: _requestComputeRolloutModeChange,
                    onRunBenchmark: _runComputeBenchmark,
                  ),
                  const SizedBox(height: 20),
                  ComputeGovernanceActivityBoard(
                    entries: _computeActivity,
                    isLoading: widget.computeGovernanceViewModel!.isLoading,
                    onOpenOperation: _openComputeGovernanceActivity,
                  ),
                ],
              ],
            ),
          ),
        ],
        if (widget.controlTaskViewModel != null ||
            widget.approvalQueueViewModel != null ||
            widget.operationConsoleViewModel != null) ...[
          const SizedBox(height: 20),
          ProgressiveDetailSection(
            title: '任务与审批',
            summary: '控制任务、审批队列和运行控制台统一收口，避免和概览信息混排。',
            icon: Icons.fact_check_rounded,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (widget.controlTaskViewModel != null)
                  ControlTaskBoard(
                    tasks: _controlTasks,
                    isLoading: widget.controlTaskViewModel!.isLoading,
                    errorMessage: widget.controlTaskViewModel!.errorMessage,
                    onRetry: _refreshSharedProjection,
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
                if (widget.approvalQueueViewModel != null) ...[
                  if (widget.controlTaskViewModel != null)
                    const SizedBox(height: 20),
                  ApprovalQueueBoard(
                    jobs: _approvalJobs,
                    isLoading: widget.approvalQueueViewModel!.isLoading,
                    errorMessage: widget.approvalQueueViewModel!.errorMessage,
                    onRefresh: _refreshSharedProjection,
                    onApprove: (job) => _resolveApproval(job, approved: true),
                    onReject: (job) => _resolveApproval(job, approved: false),
                    isUpdating: widget.approvalQueueViewModel!.isUpdating,
                    onOpenDetails: (job) => _openOperationConsole(
                      job.operationId ?? job.jobId,
                      seed: job,
                    ),
                  ),
                ],
                if (widget.operationConsoleViewModel != null) ...[
                  if (widget.controlTaskViewModel != null ||
                      widget.approvalQueueViewModel != null)
                    const SizedBox(height: 20),
                  OperationConsoleBoard(
                    viewModel: widget.operationConsoleViewModel!,
                    onApprove: () =>
                        _resolveSelectedOperationApproval(approved: true),
                    onReject: () =>
                        _resolveSelectedOperationApproval(approved: false),
                    onRetry: _retrySelectedOperation,
                    onCancel: _cancelSelectedOperation,
                  ),
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }

  void _openOverviewChainByKey(
    DashboardSummary summary,
    String key, {
    required String source,
  }) {
    final chain = _chainFor(summary, key);
    if (chain != null) {
      _openChainWorkspace(chain, source: source);
      return;
    }

    switch (key) {
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
      default:
        widget.onNavigateToTab(4);
    }
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

class _OverviewInsightCard extends StatelessWidget {
  const _OverviewInsightCard({
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.body,
    this.bodyChild,
  });

  final String title;
  final String subtitle;
  final Color accent;
  final String body;
  final Widget? bodyChild;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: AppTextStyles.h4.copyWith(color: AppColors.textPrimary),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (body.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              body,
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
          ],
          if (bodyChild != null) ...[const SizedBox(height: 12), bodyChild!],
        ],
      ),
    );
  }
}

class _OverviewChainCard extends StatelessWidget {
  const _OverviewChainCard({
    required this.title,
    required this.subtitle,
    required this.description,
    required this.actionLabel,
    required this.actionIcon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final String description;
  final String actionLabel;
  final IconData actionIcon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
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
          const SizedBox(height: 10),
          Text(
            description,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.bodyMedium,
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: onTap,
            icon: Icon(actionIcon),
            label: Text(actionLabel),
          ),
        ],
      ),
    );
  }
}

class _DeferredSectionsPlaceholder extends StatelessWidget {
  const _DeferredSectionsPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          const SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2.2),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              '正在延迟加载资产与审计区块，优先保证首屏控制面响应。',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
