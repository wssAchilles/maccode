library;

import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/compute_rollout_policy.dart';
import '../models/control_task_record.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../models/main_shell_projection.dart';
import '../models/shell_action_outcome.dart';
import '../models/shell_runtime_intent.dart';
import '../models/shell_runtime_snapshot.dart';
import '../models/workbench_runtime_models.dart';
import '../utils/main_shell_projection_builder.dart';
import 'approval_queue_view_model.dart';
import 'compute_governance_view_model.dart';
import 'control_task_view_model.dart';
import 'dashboard_view_model.dart';
import 'job_feed_registry.dart';
import 'main_shell_action_coordinator.dart';
import 'operation_console_view_model.dart';
import 'shell_operation_session_controller.dart';
import 'shell_runtime_action_state_machine.dart';
import 'shell_runtime_notification_center.dart';
import 'shell_runtime_snapshot_view_model.dart';

class MainShellRuntimeViewModel extends ChangeNotifier {
  MainShellRuntimeViewModel({
    DashboardViewModel? dashboardViewModel,
    ComputeGovernanceViewModel? computeGovernanceViewModel,
    ControlTaskViewModel? controlTaskViewModel,
    ApprovalQueueViewModel? approvalQueueViewModel,
    OperationConsoleViewModel? operationConsoleViewModel,
    JobFeedRegistry? jobFeedRegistry,
    ShellRuntimeSnapshotViewModel? snapshotViewModel,
  }) : _dashboardViewModel = dashboardViewModel ?? DashboardViewModel(),
       _ownsDashboardViewModel = dashboardViewModel == null,
       _computeGovernanceViewModel =
           computeGovernanceViewModel ?? ComputeGovernanceViewModel(),
       _ownsComputeGovernanceViewModel = computeGovernanceViewModel == null,
       _controlTaskViewModel = controlTaskViewModel ?? ControlTaskViewModel(),
       _ownsControlTaskViewModel = controlTaskViewModel == null,
       _approvalQueueViewModel =
           approvalQueueViewModel ?? ApprovalQueueViewModel(),
       _ownsApprovalQueueViewModel = approvalQueueViewModel == null,
       _operationConsoleViewModel =
           operationConsoleViewModel ?? OperationConsoleViewModel(),
       _ownsOperationConsoleViewModel = operationConsoleViewModel == null,
       _jobFeedRegistry = jobFeedRegistry ?? JobFeedRegistry(),
       _ownsJobFeedRegistry = jobFeedRegistry == null,
       _snapshotViewModel =
           snapshotViewModel ?? ShellRuntimeSnapshotViewModel(),
       _ownsSnapshotViewModel = snapshotViewModel == null {
    _actionStateMachine = ShellRuntimeActionStateMachine();
    _notificationCenter = ShellRuntimeNotificationCenter();
    _operationSessionController = ShellOperationSessionController();
    _childListenables = <Listenable>[
      _snapshotViewModel,
      _dashboardViewModel,
      _computeGovernanceViewModel,
      _controlTaskViewModel,
      _approvalQueueViewModel,
      _operationConsoleViewModel,
      _jobFeedRegistry,
      _actionStateMachine,
      _notificationCenter,
      _operationSessionController,
    ];
    for (final listenable in _childListenables) {
      listenable.addListener(_relayChildUpdate);
    }
    _actionCoordinator = MainShellActionCoordinator(
      computeGovernanceViewModel: _computeGovernanceViewModel,
      controlTaskViewModel: _controlTaskViewModel,
      approvalQueueViewModel: _approvalQueueViewModel,
      operationConsoleViewModel: _operationConsoleViewModel,
      jobFeedRegistry: _jobFeedRegistry,
    );
    _projection = _buildProjection();
  }

  late final List<Listenable> _childListenables;
  final DashboardViewModel _dashboardViewModel;
  final bool _ownsDashboardViewModel;
  final ComputeGovernanceViewModel _computeGovernanceViewModel;
  final bool _ownsComputeGovernanceViewModel;
  final ControlTaskViewModel _controlTaskViewModel;
  final bool _ownsControlTaskViewModel;
  final ApprovalQueueViewModel _approvalQueueViewModel;
  final bool _ownsApprovalQueueViewModel;
  final OperationConsoleViewModel _operationConsoleViewModel;
  final bool _ownsOperationConsoleViewModel;
  final JobFeedRegistry _jobFeedRegistry;
  final bool _ownsJobFeedRegistry;
  final ShellRuntimeSnapshotViewModel _snapshotViewModel;
  final bool _ownsSnapshotViewModel;
  late final MainShellActionCoordinator _actionCoordinator;
  late final ShellRuntimeActionStateMachine _actionStateMachine;
  late final ShellRuntimeNotificationCenter _notificationCenter;
  late final ShellOperationSessionController _operationSessionController;

  bool _isDisposed = false;
  bool _isInitialized = false;
  bool _operationsWorkspaceReady = false;
  int _intentSequence = 0;
  WorkbenchTab _activeTab = WorkbenchTab.operationsHub;
  bool _panelVisible = false;
  ShellRuntimePanelKind _panelKind = ShellRuntimePanelKind.approvals;
  late MainShellProjection _projection;

  DashboardViewModel get dashboardViewModel => _dashboardViewModel;
  ComputeGovernanceViewModel get computeGovernanceViewModel =>
      _computeGovernanceViewModel;
  ControlTaskViewModel get controlTaskViewModel => _controlTaskViewModel;
  ApprovalQueueViewModel get approvalQueueViewModel => _approvalQueueViewModel;
  OperationConsoleViewModel get operationConsoleViewModel =>
      _operationConsoleViewModel;
  JobFeedRegistry get jobFeeds => _jobFeedRegistry;
  ShellRuntimeNotificationCenter get notificationCenter => _notificationCenter;
  ShellOperationSessionController get operationSession =>
      _operationSessionController;

  WorkbenchTab get activeTab => _activeTab;
  bool get panelVisible => _panelVisible;
  ShellRuntimePanelKind get panelKind => _panelKind;
  MainShellProjection get projection => _projection;
  bool get hasSelectedOperation =>
      _operationConsoleViewModel.selectedOperation != null;
  ShellRuntimeSnapshot? get sharedSnapshot => _snapshotViewModel.snapshot;

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }
    _isInitialized = true;
    await _snapshotViewModel.initialize();
    final snapshot = _snapshotViewModel.snapshot;
    if (snapshot != null) {
      _hydrateSharedSnapshot(snapshot);
    } else {
      await Future.wait([
        _dashboardViewModel.initialize(),
        _approvalQueueViewModel.initialize(),
      ]);
    }
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> activateTab(WorkbenchTab tab) async {
    _activeTab = tab;
    await initialize();
    if (tab == WorkbenchTab.operationsHub && !_operationsWorkspaceReady) {
      _operationsWorkspaceReady = true;
      if (_snapshotViewModel.snapshot == null) {
        await Future.wait([
          _computeGovernanceViewModel.initialize(),
          _controlTaskViewModel.initialize(),
        ]);
      }
    }
    await _jobFeedRegistry.activateForTab(tab);
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> refreshSharedSnapshot({bool force = false}) async {
    final snapshot = await _snapshotViewModel.loadSnapshot(force: force);
    if (snapshot != null) {
      _hydrateSharedSnapshot(snapshot);
    }
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> showPanel(
    ShellRuntimePanelKind kind, {
    bool visible = true,
  }) async {
    _panelKind = kind;
    _panelVisible = visible;
    if (kind == ShellRuntimePanelKind.approvals) {
      await _approvalQueueViewModel.initialize();
    }
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  void closePanel() {
    if (!_panelVisible) {
      _syncOperationConsoleActivity();
      return;
    }
    _panelVisible = false;
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> openOperation(
    String operationId, {
    JobRecord? seed,
    bool openPanel = true,
  }) async {
    _operationSessionController.beginSelection(
      operationId: operationId,
      originTab: _activeTab,
    );
    await _operationConsoleViewModel.selectOperation(operationId, seed: seed);
    _panelKind = ShellRuntimePanelKind.operations;
    _panelVisible = openPanel;
    _syncOperationConsoleActivity();
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
    final current = _operationConsoleViewModel.selectedOperation;
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
    final current = _operationConsoleViewModel.selectedOperation;
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
    final current = _operationConsoleViewModel.selectedOperation;
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
      sourceTab: _activeTab,
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
      _panelKind = ShellRuntimePanelKind.operations;
      _panelVisible = true;
      final operationId = operation.operationId ?? operation.jobId;
      if (_operationConsoleViewModel.selectedOperationId != operationId) {
        _operationSessionController.beginSelection(
          operationId: operationId,
          originTab: _activeTab,
        );
      }
    }
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
    return outcome;
  }

  void _syncOperationConsoleActivity() {
    final shouldStream =
        _activeTab == WorkbenchTab.operationsHub ||
        (_panelVisible && _panelKind == ShellRuntimePanelKind.operations);
    _operationConsoleViewModel.setWorkspaceActive(shouldStream);
  }

  void _relayChildUpdate() {
    _operationSessionController.syncFromConsole(_operationConsoleViewModel);
    final snapshot = _snapshotViewModel.snapshot;
    final snapshotSummary = _snapshotViewModel.snapshot?.summary;
    _notificationCenter.recordBackendAlerts(
      snapshotSummary?.alerts ??
          _dashboardViewModel.summary?.alerts ??
          const <DashboardAlert>[],
      sourceTab: _activeTab,
    );
    _notificationCenter.recordProjectionDegraded(
      snapshot?.degradedSections ?? const <ShellRuntimeDegradedSection>[],
      sourceTab: _activeTab,
    );
    _notificationCenter.recordSessionUpdate(
      _operationSessionController.session,
    );
    _notifySafely(rebuildProjection: true);
  }

  MainShellProjection _buildProjection() {
    final snapshot = _snapshotViewModel.snapshot;
    return buildMainShellProjection(
      activeTab: _activeTab,
      panelVisible: _panelVisible,
      panelKind: _panelKind,
      summary: snapshot?.summary ?? _dashboardViewModel.summary,
      approvalJobs: snapshot?.approvalJobs ?? _approvalQueueViewModel.jobs,
      controlTasks: snapshot?.controlTasks ?? _controlTaskViewModel.tasks,
      computePolicy:
          snapshot?.computePolicy ?? _computeGovernanceViewModel.policy,
      computeActivity:
          snapshot?.computeActivity ??
          _computeGovernanceViewModel.recentActivity,
      selectedOperation: _operationConsoleViewModel.selectedOperation,
      activeAction: _actionStateMachine.activeAction,
      recentActions: _actionStateMachine.recentActions,
      notifications: _notificationCenter.notifications,
      operationSession: _operationSessionController.session,
      snapshotGeneratedAt: snapshot?.generatedAt,
      degradedSections:
          snapshot?.degradedSections ?? const <ShellRuntimeDegradedSection>[],
    );
  }

  void _hydrateSharedSnapshot(ShellRuntimeSnapshot snapshot) {
    _dashboardViewModel.hydrateSummary(snapshot.summary);
    _approvalQueueViewModel.hydrateQueue(snapshot.approvalJobs);
    _controlTaskViewModel.hydrateTasks(snapshot.controlTasks);
    _computeGovernanceViewModel.hydrateSnapshot(
      policy: snapshot.computePolicy,
      activity: snapshot.computeActivity,
    );
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
    if (_ownsJobFeedRegistry) {
      _jobFeedRegistry.dispose();
    }
    if (_ownsSnapshotViewModel) {
      _snapshotViewModel.dispose();
    }
    if (_ownsOperationConsoleViewModel) {
      _operationConsoleViewModel.dispose();
    }
    if (_ownsApprovalQueueViewModel) {
      _approvalQueueViewModel.dispose();
    }
    if (_ownsControlTaskViewModel) {
      _controlTaskViewModel.dispose();
    }
    if (_ownsComputeGovernanceViewModel) {
      _computeGovernanceViewModel.dispose();
    }
    if (_ownsDashboardViewModel) {
      _dashboardViewModel.dispose();
    }
    super.dispose();
  }
}
