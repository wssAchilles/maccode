library;

import '../models/dashboard_summary.dart';
import '../models/main_shell_projection.dart';
import '../models/shell_runtime_snapshot.dart';
import '../utils/main_shell_projection_builder.dart';
import 'shell_navigation_state.dart';
import 'shell_operation_session_controller.dart';
import 'shell_runtime_action_state_machine.dart';
import 'shell_runtime_notification_center.dart';
import 'workspace_runtime_registry.dart';

class ShellProjectionController {
  ShellProjectionController({
    required this.navigation,
    required this.registry,
    required this.actionStateMachine,
    required this.notificationCenter,
    required this.operationSessionController,
  });

  final ShellNavigationState navigation;
  final WorkspaceRuntimeRegistry registry;
  final ShellRuntimeActionStateMachine actionStateMachine;
  final ShellRuntimeNotificationCenter notificationCenter;
  final ShellOperationSessionController operationSessionController;

  MainShellProjection build() {
    final snapshot = registry.snapshot;
    return buildMainShellProjection(
      activeTab: navigation.activeTab,
      panelVisible: navigation.panelVisible,
      panelKind: navigation.panelKind,
      summary: snapshot?.summary ?? registry.dashboardViewModel.summary,
      approvalJobs:
          snapshot?.approvalJobs ?? registry.approvalQueueViewModel.jobs,
      controlTasks:
          snapshot?.controlTasks ?? registry.controlTaskViewModel.tasks,
      computePolicy:
          snapshot?.computePolicy ?? registry.computeGovernanceViewModel.policy,
      computeActivity:
          snapshot?.computeActivity ??
          registry.computeGovernanceViewModel.recentActivity,
      selectedOperation: registry.operationConsoleViewModel.selectedOperation,
      activeAction: actionStateMachine.activeAction,
      recentActions: actionStateMachine.recentActions,
      notifications: notificationCenter.notifications,
      operationSession: operationSessionController.session,
      snapshotGeneratedAt: snapshot?.generatedAt,
      degradedSections:
          snapshot?.degradedSections ?? const <ShellRuntimeDegradedSection>[],
    );
  }

  void recordProjectionSignals() {
    final snapshot = registry.snapshot;
    final DashboardSummary? summary =
        snapshot?.summary ?? registry.dashboardViewModel.summary;
    notificationCenter.recordBackendAlerts(
      summary?.alerts ?? const <DashboardAlert>[],
      sourceTab: navigation.activeTab,
    );
    notificationCenter.recordProjectionDegraded(
      snapshot?.degradedSections ?? const <ShellRuntimeDegradedSection>[],
      sourceTab: navigation.activeTab,
    );
    notificationCenter.recordSessionUpdate(operationSessionController.session);
  }
}
