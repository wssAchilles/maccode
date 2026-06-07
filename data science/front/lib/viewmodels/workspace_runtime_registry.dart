library;

import 'package:flutter/foundation.dart';

import '../models/shell_runtime_snapshot.dart';
import '../models/workbench_runtime_models.dart';
import 'approval_queue_view_model.dart';
import 'compute_governance_view_model.dart';
import 'control_task_view_model.dart';
import 'dashboard_view_model.dart';
import 'job_feed_registry.dart';
import 'operation_console_view_model.dart';
import 'shell_runtime_snapshot_view_model.dart';

class WorkspaceRuntimeRegistry {
  WorkspaceRuntimeRegistry({
    DashboardViewModel? dashboardViewModel,
    ComputeGovernanceViewModel? computeGovernanceViewModel,
    ControlTaskViewModel? controlTaskViewModel,
    ApprovalQueueViewModel? approvalQueueViewModel,
    OperationConsoleViewModel? operationConsoleViewModel,
    JobFeedRegistry? jobFeedRegistry,
    ShellRuntimeSnapshotViewModel? snapshotViewModel,
  }) : dashboardViewModel = dashboardViewModel ?? DashboardViewModel(),
       ownsDashboardViewModel = dashboardViewModel == null,
       computeGovernanceViewModel =
           computeGovernanceViewModel ?? ComputeGovernanceViewModel(),
       ownsComputeGovernanceViewModel = computeGovernanceViewModel == null,
       controlTaskViewModel = controlTaskViewModel ?? ControlTaskViewModel(),
       ownsControlTaskViewModel = controlTaskViewModel == null,
       approvalQueueViewModel =
           approvalQueueViewModel ?? ApprovalQueueViewModel(),
       ownsApprovalQueueViewModel = approvalQueueViewModel == null,
       operationConsoleViewModel =
           operationConsoleViewModel ?? OperationConsoleViewModel(),
       ownsOperationConsoleViewModel = operationConsoleViewModel == null,
       jobFeedRegistry = jobFeedRegistry ?? JobFeedRegistry(),
       ownsJobFeedRegistry = jobFeedRegistry == null,
       snapshotViewModel = snapshotViewModel ?? ShellRuntimeSnapshotViewModel(),
       ownsSnapshotViewModel = snapshotViewModel == null;

  final DashboardViewModel dashboardViewModel;
  final bool ownsDashboardViewModel;
  final ComputeGovernanceViewModel computeGovernanceViewModel;
  final bool ownsComputeGovernanceViewModel;
  final ControlTaskViewModel controlTaskViewModel;
  final bool ownsControlTaskViewModel;
  final ApprovalQueueViewModel approvalQueueViewModel;
  final bool ownsApprovalQueueViewModel;
  final OperationConsoleViewModel operationConsoleViewModel;
  final bool ownsOperationConsoleViewModel;
  final JobFeedRegistry jobFeedRegistry;
  final bool ownsJobFeedRegistry;
  final ShellRuntimeSnapshotViewModel snapshotViewModel;
  final bool ownsSnapshotViewModel;

  bool _isInitialized = false;
  bool _operationsWorkspaceReady = false;

  List<Listenable> get listenables => <Listenable>[
    snapshotViewModel,
    dashboardViewModel,
    computeGovernanceViewModel,
    controlTaskViewModel,
    approvalQueueViewModel,
    operationConsoleViewModel,
    jobFeedRegistry,
  ];

  ShellRuntimeSnapshot? get snapshot => snapshotViewModel.snapshot;

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }
    _isInitialized = true;
    await snapshotViewModel.initialize();
    final currentSnapshot = snapshot;
    if (currentSnapshot != null) {
      hydrateSnapshot(currentSnapshot);
      return;
    }
    await Future.wait([
      dashboardViewModel.initialize(),
      approvalQueueViewModel.initialize(),
    ]);
  }

  Future<void> activateTab(WorkbenchTab tab) async {
    await initialize();
    if (tab == WorkbenchTab.operationsHub && !_operationsWorkspaceReady) {
      _operationsWorkspaceReady = true;
      if (snapshot == null) {
        await Future.wait([
          computeGovernanceViewModel.initialize(),
          controlTaskViewModel.initialize(),
        ]);
      }
    }
    await jobFeedRegistry.activateForTab(tab);
  }

  Future<ShellRuntimeSnapshot?> refreshSnapshot({bool force = false}) async {
    final currentSnapshot = await snapshotViewModel.loadSnapshot(force: force);
    if (currentSnapshot != null) {
      hydrateSnapshot(currentSnapshot);
    }
    return currentSnapshot;
  }

  void hydrateSnapshot(ShellRuntimeSnapshot snapshot) {
    dashboardViewModel.hydrateSummary(snapshot.summary);
    approvalQueueViewModel.hydrateQueue(snapshot.approvalJobs);
    controlTaskViewModel.hydrateTasks(snapshot.controlTasks);
    computeGovernanceViewModel.hydrateSnapshot(
      policy: snapshot.computePolicy,
      activity: snapshot.computeActivity,
    );
  }

  void dispose() {
    if (ownsJobFeedRegistry) {
      jobFeedRegistry.dispose();
    }
    if (ownsSnapshotViewModel) {
      snapshotViewModel.dispose();
    }
    if (ownsOperationConsoleViewModel) {
      operationConsoleViewModel.dispose();
    }
    if (ownsApprovalQueueViewModel) {
      approvalQueueViewModel.dispose();
    }
    if (ownsControlTaskViewModel) {
      controlTaskViewModel.dispose();
    }
    if (ownsComputeGovernanceViewModel) {
      computeGovernanceViewModel.dispose();
    }
    if (ownsDashboardViewModel) {
      dashboardViewModel.dispose();
    }
  }
}
