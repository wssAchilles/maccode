library;

import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/job_record.dart';
import '../models/main_shell_projection.dart';
import '../models/workbench_runtime_models.dart';
import '../utils/main_shell_projection_builder.dart';
import 'approval_queue_view_model.dart';
import 'compute_governance_view_model.dart';
import 'control_task_view_model.dart';
import 'dashboard_view_model.dart';
import 'job_feed_registry.dart';
import 'operation_console_view_model.dart';

class MainShellRuntimeViewModel extends ChangeNotifier {
  MainShellRuntimeViewModel({
    DashboardViewModel? dashboardViewModel,
    ComputeGovernanceViewModel? computeGovernanceViewModel,
    ControlTaskViewModel? controlTaskViewModel,
    ApprovalQueueViewModel? approvalQueueViewModel,
    OperationConsoleViewModel? operationConsoleViewModel,
    JobFeedRegistry? jobFeedRegistry,
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
       _ownsJobFeedRegistry = jobFeedRegistry == null {
    _childListenables = <Listenable>[
      _dashboardViewModel,
      _computeGovernanceViewModel,
      _controlTaskViewModel,
      _approvalQueueViewModel,
      _operationConsoleViewModel,
      _jobFeedRegistry,
    ];
    for (final listenable in _childListenables) {
      listenable.addListener(_relayChildUpdate);
    }
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

  bool _isDisposed = false;
  bool _isInitialized = false;
  bool _operationsWorkspaceReady = false;
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

  WorkbenchTab get activeTab => _activeTab;
  bool get panelVisible => _panelVisible;
  ShellRuntimePanelKind get panelKind => _panelKind;
  MainShellProjection get projection => _projection;
  bool get hasSelectedOperation =>
      _operationConsoleViewModel.selectedOperation != null;

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }
    _isInitialized = true;
    await Future.wait([
      _dashboardViewModel.initialize(),
      _approvalQueueViewModel.initialize(),
    ]);
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<void> activateTab(WorkbenchTab tab) async {
    _activeTab = tab;
    await initialize();
    if (tab == WorkbenchTab.operationsHub && !_operationsWorkspaceReady) {
      _operationsWorkspaceReady = true;
      await Future.wait([
        _computeGovernanceViewModel.initialize(),
        _controlTaskViewModel.initialize(),
      ]);
    }
    await _jobFeedRegistry.activateForTab(tab);
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
    await _operationConsoleViewModel.selectOperation(operationId, seed: seed);
    _panelKind = ShellRuntimePanelKind.operations;
    _panelVisible = openPanel;
    _syncOperationConsoleActivity();
    _notifySafely(rebuildProjection: true);
  }

  Future<JobRecord?> resolveQueuedApproval(
    JobRecord job, {
    required bool approved,
    String? message,
  }) async {
    final updated = await _approvalQueueViewModel.resolve(
      job,
      approved: approved,
      message: message,
    );
    if (updated == null) {
      return null;
    }
    await Future.wait([
      _controlTaskViewModel.loadControlTasks(),
      _approvalQueueViewModel.loadQueue(),
    ]);
    await openOperation(
      updated.operationId ?? updated.jobId,
      seed: updated,
      openPanel: true,
    );
    return updated;
  }

  Future<JobRecord?> resolveSelectedOperationApproval({
    required bool approved,
    String? message,
  }) async {
    final updated = await _operationConsoleViewModel.resolveSelectedApproval(
      approved: approved,
      message: message,
    );
    if (updated == null) {
      return null;
    }
    await Future.wait([
      _approvalQueueViewModel.loadQueue(),
      _controlTaskViewModel.loadControlTasks(),
    ]);
    return updated;
  }

  Future<JobRecord?> retrySelectedOperation() async {
    final updated = await _operationConsoleViewModel.retrySelected();
    if (updated != null) {
      await _controlTaskViewModel.loadControlTasks();
    }
    return updated;
  }

  Future<JobRecord?> cancelSelectedOperation() async {
    final updated = await _operationConsoleViewModel.cancelSelected();
    if (updated != null) {
      await Future.wait([
        _controlTaskViewModel.loadControlTasks(),
        _approvalQueueViewModel.loadQueue(),
      ]);
    }
    return updated;
  }

  void _syncOperationConsoleActivity() {
    final shouldStream =
        _activeTab == WorkbenchTab.operationsHub ||
        (_panelVisible && _panelKind == ShellRuntimePanelKind.operations);
    _operationConsoleViewModel.setWorkspaceActive(shouldStream);
  }

  void _relayChildUpdate() {
    _notifySafely(rebuildProjection: true);
  }

  MainShellProjection _buildProjection() {
    return buildMainShellProjection(
      activeTab: _activeTab,
      panelVisible: _panelVisible,
      panelKind: _panelKind,
      summary: _dashboardViewModel.summary,
      approvalJobs: _approvalQueueViewModel.jobs,
      controlTasks: _controlTaskViewModel.tasks,
      computePolicy: _computeGovernanceViewModel.policy,
      computeActivity: _computeGovernanceViewModel.recentActivity,
      selectedOperation: _operationConsoleViewModel.selectedOperation,
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
