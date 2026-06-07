library;

import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/compute_rollout_policy.dart';
import '../models/control_task_record.dart';
import '../models/job_record.dart';
import '../models/main_shell_projection.dart';
import '../models/shell_action_outcome.dart';
import '../models/shell_runtime_intent.dart';
import '../models/shell_runtime_snapshot.dart';
import '../models/workbench_runtime_models.dart';
import 'approval_queue_view_model.dart';
import 'compute_governance_view_model.dart';
import 'control_task_view_model.dart';
import 'dashboard_view_model.dart';
import 'job_feed_registry.dart';
import 'main_shell_action_coordinator.dart';
import 'operation_runtime_controller.dart';
import 'operation_console_view_model.dart';
import 'shell_navigation_state.dart';
import 'shell_operation_session_controller.dart';
import 'shell_projection_controller.dart';
import 'shell_runtime_action_state_machine.dart';
import 'shell_runtime_notification_center.dart';
import 'shell_runtime_snapshot_view_model.dart';
import 'workspace_runtime_registry.dart';

class MainShellRuntimeViewModel extends ChangeNotifier {
  MainShellRuntimeViewModel({
    DashboardViewModel? dashboardViewModel,
    ComputeGovernanceViewModel? computeGovernanceViewModel,
    ControlTaskViewModel? controlTaskViewModel,
    ApprovalQueueViewModel? approvalQueueViewModel,
    OperationConsoleViewModel? operationConsoleViewModel,
    JobFeedRegistry? jobFeedRegistry,
    ShellRuntimeSnapshotViewModel? snapshotViewModel,
  }) {
    _registry = WorkspaceRuntimeRegistry(
      dashboardViewModel: dashboardViewModel,
      computeGovernanceViewModel: computeGovernanceViewModel,
      controlTaskViewModel: controlTaskViewModel,
      approvalQueueViewModel: approvalQueueViewModel,
      operationConsoleViewModel: operationConsoleViewModel,
      jobFeedRegistry: jobFeedRegistry,
      snapshotViewModel: snapshotViewModel,
    );
    _navigation = ShellNavigationState();
    _actionStateMachine = ShellRuntimeActionStateMachine();
    _notificationCenter = ShellRuntimeNotificationCenter();
    _operationSessionController = ShellOperationSessionController();
    _childListenables = <Listenable>[
      _navigation,
      ..._registry.listenables,
      _actionStateMachine,
      _notificationCenter,
      _operationSessionController,
    ];
    for (final listenable in _childListenables) {
      listenable.addListener(_relayChildUpdate);
    }
    _actionCoordinator = MainShellActionCoordinator(
      computeGovernanceViewModel: _registry.computeGovernanceViewModel,
      controlTaskViewModel: _registry.controlTaskViewModel,
      approvalQueueViewModel: _registry.approvalQueueViewModel,
      operationConsoleViewModel: _registry.operationConsoleViewModel,
      jobFeedRegistry: _registry.jobFeedRegistry,
    );
    _operationRuntime = OperationRuntimeController(
      navigation: _navigation,
      operationConsoleViewModel: _registry.operationConsoleViewModel,
      operationSessionController: _operationSessionController,
    );
    _projectionController = ShellProjectionController(
      navigation: _navigation,
      registry: _registry,
      actionStateMachine: _actionStateMachine,
      notificationCenter: _notificationCenter,
      operationSessionController: _operationSessionController,
    );
    _projection = _buildProjection();
  }

  late final List<Listenable> _childListenables;
  late final WorkspaceRuntimeRegistry _registry;
  late final ShellNavigationState _navigation;
  late final MainShellActionCoordinator _actionCoordinator;
  late final ShellRuntimeActionStateMachine _actionStateMachine;
  late final ShellRuntimeNotificationCenter _notificationCenter;
  late final ShellOperationSessionController _operationSessionController;
  late final ShellProjectionController _projectionController;
  late final OperationRuntimeController _operationRuntime;

  bool _isDisposed = false;
  int _intentSequence = 0;
  late MainShellProjection _projection;

  DashboardViewModel get dashboardViewModel => _registry.dashboardViewModel;
  ComputeGovernanceViewModel get computeGovernanceViewModel =>
      _registry.computeGovernanceViewModel;
  ControlTaskViewModel get controlTaskViewModel =>
      _registry.controlTaskViewModel;
  ApprovalQueueViewModel get approvalQueueViewModel =>
      _registry.approvalQueueViewModel;
  OperationConsoleViewModel get operationConsoleViewModel =>
      _registry.operationConsoleViewModel;
  JobFeedRegistry get jobFeeds => _registry.jobFeedRegistry;
  ShellRuntimeNotificationCenter get notificationCenter => _notificationCenter;
  ShellOperationSessionController get operationSession =>
      _operationSessionController;

  WorkbenchTab get activeTab => _navigation.activeTab;
  bool get panelVisible => _navigation.panelVisible;
  ShellRuntimePanelKind get panelKind => _navigation.panelKind;
  MainShellProjection get projection => _projection;
  bool get hasSelectedOperation =>
      _registry.operationConsoleViewModel.selectedOperation != null;
  ShellRuntimeSnapshot? get sharedSnapshot => _registry.snapshot;

  Future<void> initialize() async {
    await _registry.initialize();
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> activateTab(WorkbenchTab tab) async {
    _navigation.activateTab(tab);
    await _registry.activateTab(tab);
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> refreshSharedSnapshot({bool force = false}) async {
    await _registry.refreshSnapshot(force: force);
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> showPanel(
    ShellRuntimePanelKind kind, {
    bool visible = true,
  }) async {
    _navigation.showPanel(kind, visible: visible);
    if (kind == ShellRuntimePanelKind.approvals) {
      await _registry.approvalQueueViewModel.initialize();
    }
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  void closePanel() {
    if (!_navigation.panelVisible) {
      _syncOperationConsoleActivity();
      return;
    }
    _navigation.closePanel();
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> openOperation(
    String operationId, {
    JobRecord? seed,
    bool openPanel = true,
  }) async {
    await _operationRuntime.openOperation(
      operationId,
      seed: seed,
      openPanel: openPanel,
    );
    _notifySafely(rebuildProjection: true);
  }

  void markNotificationRead(String notificationId) {
    _notificationCenter.markRead(notificationId);
  }

  void markAllNotificationsRead() {
    _notificationCenter.markAllRead();
  }

  void dismissNotification(String notificationId) {
    _notificationCenter.dismiss(notificationId);
  }

  Future<JobRecord?> resolveQueuedApproval(
    JobRecord job, {
    required bool approved,
    String? message,
  }) async => (await resolveQueuedApprovalAction(
    job,
    approved: approved,
    message: message,
  )).data;

  Future<ShellActionOutcome<JobRecord>> resolveQueuedApprovalAction(
    JobRecord job, {
    required bool approved,
    String? message,
  }) {
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.approval,
      kind: ShellIntentKind.resolveApproval,
      label: approved ? '批准待审批任务' : '驳回待审批任务',
      resourceId: job.operationId ?? job.jobId,
      resourceLabel: job.displayTitle,
      run: () => _actionCoordinator.resolveQueuedApproval(
        job,
        approved: approved,
        message: message,
      ),
    );
  }

  Future<JobRecord?> resolveSelectedOperationApproval({
    required bool approved,
    String? message,
  }) async => (await resolveSelectedOperationApprovalAction(
    approved: approved,
    message: message,
  )).data;

  Future<ShellActionOutcome<JobRecord>> resolveSelectedOperationApprovalAction({
    required bool approved,
    String? message,
  }) {
    final current = _registry.operationConsoleViewModel.selectedOperation;
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.operation,
      kind: ShellIntentKind.resolveApproval,
      label: approved ? '批准当前运行' : '驳回当前运行',
      resourceId: current?.operationId ?? current?.jobId,
      resourceLabel: current?.displayTitle,
      run: () => _actionCoordinator.resolveSelectedOperationApproval(
        approved: approved,
        message: message,
      ),
    );
  }

  Future<JobRecord?> retrySelectedOperation() async =>
      (await retrySelectedOperationAction()).data;

  Future<ShellActionOutcome<JobRecord>> retrySelectedOperationAction() {
    final current = _registry.operationConsoleViewModel.selectedOperation;
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.operation,
      kind: ShellIntentKind.retryOperation,
      label: '重试当前运行',
      resourceId: current?.operationId ?? current?.jobId,
      resourceLabel: current?.displayTitle,
      run: _actionCoordinator.retrySelectedOperation,
    );
  }

  Future<JobRecord?> cancelSelectedOperation() async =>
      (await cancelSelectedOperationAction()).data;

  Future<ShellActionOutcome<JobRecord>> cancelSelectedOperationAction() {
    final current = _registry.operationConsoleViewModel.selectedOperation;
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.operation,
      kind: ShellIntentKind.cancelOperation,
      label: '取消当前运行',
      resourceId: current?.operationId ?? current?.jobId,
      resourceLabel: current?.displayTitle,
      run: _actionCoordinator.cancelSelectedOperation,
    );
  }

  Future<ShellActionOutcome<JobRecord>> runControlTask(
    ControlTaskRecord task, {
    Map<String, dynamic>? inputOverrides,
    String trigger = 'manual',
  }) {
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.controlTask,
      kind: ShellIntentKind.runControlTask,
      label: '触发规划任务',
      resourceId: task.id,
      resourceLabel: task.title,
      run: () => _actionCoordinator.runControlTask(
        task,
        inputOverrides: inputOverrides,
        trigger: trigger,
      ),
    );
  }

  Future<ShellActionOutcome<ControlTaskRecord>> setControlTaskEnabled(
    ControlTaskRecord task, {
    required bool enabled,
  }) {
    return _dispatchIntent<ControlTaskRecord>(
      domain: ShellIntentDomain.controlTask,
      kind: ShellIntentKind.updateControlTask,
      label: enabled ? '恢复规划任务' : '暂停规划任务',
      resourceId: task.id,
      resourceLabel: task.title,
      run: () =>
          _actionCoordinator.setControlTaskEnabled(task, enabled: enabled),
      openOperationsPanel: false,
    );
  }

  Future<ShellActionOutcome<ControlTaskRecord>> setControlTaskApprovalPolicy(
    ControlTaskRecord task, {
    required Map<String, dynamic> approvalPolicy,
  }) {
    return _dispatchIntent<ControlTaskRecord>(
      domain: ShellIntentDomain.controlTask,
      kind: ShellIntentKind.updateControlTask,
      label: '更新规划任务审批策略',
      resourceId: task.id,
      resourceLabel: task.title,
      run: () => _actionCoordinator.setControlTaskApprovalPolicy(
        task,
        approvalPolicy: approvalPolicy,
      ),
      openOperationsPanel: false,
    );
  }

  Future<ShellActionOutcome<ControlTaskRecord>> updateControlTaskDefinition(
    ControlTaskRecord task, {
    String? schedule,
    String? owner,
    required List<String> dependencies,
    required Map<String, dynamic> approvalPolicy,
    required Map<String, dynamic> defaultInput,
  }) {
    return _dispatchIntent<ControlTaskRecord>(
      domain: ShellIntentDomain.controlTask,
      kind: ShellIntentKind.updateControlTask,
      label: '更新规划任务定义',
      resourceId: task.id,
      resourceLabel: task.title,
      run: () => _actionCoordinator.updateControlTaskDefinition(
        task,
        schedule: schedule,
        owner: owner,
        dependencies: dependencies,
        approvalPolicy: approvalPolicy,
        defaultInput: defaultInput,
      ),
      openOperationsPanel: false,
    );
  }

  Future<ShellActionOutcome<JobRecord>> requestComputeRolloutModeChange(
    ComputeRolloutComponentPolicy component, {
    required Map<String, dynamic> targetPolicy,
    String? changeReason,
    String requestKind = 'rollout_change',
  }) {
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.computeGovernance,
      kind: ShellIntentKind.requestRolloutChange,
      label: '提交计算治理变更',
      resourceId: component.key,
      resourceLabel: component.label,
      run: () => _actionCoordinator.requestComputeRolloutModeChange(
        component,
        targetPolicy: targetPolicy,
        changeReason: changeReason,
        requestKind: requestKind,
      ),
    );
  }

  Future<ShellActionOutcome<JobRecord>> requestComputeBenchmark(
    ComputeRolloutComponentPolicy component, {
    int sampleRows = 5000,
  }) {
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.computeGovernance,
      kind: ShellIntentKind.requestBenchmark,
      label: '提交 benchmark 运行',
      resourceId: component.key,
      resourceLabel: component.label,
      run: () => _actionCoordinator.requestComputeBenchmark(
        component,
        sampleRows: sampleRows,
      ),
    );
  }

  Future<ShellActionOutcome<JobRecord>> retrySharedJob(JobRecord job) {
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.operation,
      kind: ShellIntentKind.retryOperation,
      label: '重试共享任务',
      resourceId: job.operationId ?? job.jobId,
      resourceLabel: job.displayTitle,
      run: () => _actionCoordinator.retrySharedJob(job),
    );
  }

  Future<ShellActionOutcome<JobRecord>> cancelSharedJob(JobRecord job) {
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.operation,
      kind: ShellIntentKind.cancelOperation,
      label: '取消共享任务',
      resourceId: job.operationId ?? job.jobId,
      resourceLabel: job.displayTitle,
      run: () => _actionCoordinator.cancelSharedJob(job),
    );
  }

  Future<ShellActionOutcome<JobRecord>> resolveSharedJobApproval(
    JobRecord job, {
    required bool approved,
    String? message,
  }) {
    return _dispatchIntent<JobRecord>(
      domain: ShellIntentDomain.approval,
      kind: ShellIntentKind.resolveApproval,
      label: approved ? '批准共享任务' : '驳回共享任务',
      resourceId: job.operationId ?? job.jobId,
      resourceLabel: job.displayTitle,
      run: () => _actionCoordinator.resolveSharedJobApproval(
        job,
        approved: approved,
        message: message,
      ),
    );
  }

  Future<ShellActionOutcome<T>> _dispatchIntent<T>({
    required ShellIntentDomain domain,
    required ShellIntentKind kind,
    required String label,
    required Future<ShellActionOutcome<T>> Function() run,
    String? resourceId,
    String? resourceLabel,
    bool openOperationsPanel = true,
  }) async {
    final intent = ShellRuntimeIntent(
      id: 'intent-${++_intentSequence}',
      domain: domain,
      kind: kind,
      label: label,
      sourceTab: _navigation.activeTab,
      issuedAt: DateTime.now(),
      resourceId: resourceId,
      resourceLabel: resourceLabel,
    );
    final outcome = await _actionStateMachine.dispatch<T>(
      intent: intent,
      run: run,
    );
    if (outcome.succeeded) {
      await refreshSharedSnapshot(force: true);
    }
    _notificationCenter.recordActionOutcome(intent, outcome);
    final operation = outcome.data is JobRecord
        ? outcome.data as JobRecord
        : null;
    if (operation != null && openOperationsPanel) {
      _operationRuntime.focusOperation(operation);
    }
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
    return outcome;
  }

  void _syncOperationConsoleActivity() {
    _operationRuntime.syncActivity();
  }

  void _relayChildUpdate() {
    _operationSessionController.syncFromConsole(
      _registry.operationConsoleViewModel,
    );
    _projectionController.recordProjectionSignals();
    _notifySafely(rebuildProjection: true);
  }

  MainShellProjection _buildProjection() {
    return _projectionController.build();
  }

  void _notifySafely({bool rebuildProjection = false}) {
    if (rebuildProjection) {
      _projection = _buildProjection();
    }
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    for (final listenable in _childListenables) {
      listenable.removeListener(_relayChildUpdate);
    }
    _navigation.dispose();
    _registry.dispose();
    super.dispose();
  }
}
