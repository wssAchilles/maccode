library;

import 'compute_governance_activity_entry.dart';
import 'compute_rollout_policy.dart';
import 'control_task_record.dart';
import 'dashboard_summary.dart';
import 'job_record.dart';
import 'shell_operation_session.dart';
import 'shell_runtime_action_state.dart';
import 'shell_runtime_notification.dart';
import 'shell_runtime_snapshot.dart';
import 'workbench_runtime_models.dart';

class MainShellProjection {
  const MainShellProjection({
    required this.activeTab,
    required this.activeTabLabel,
    required this.panelVisible,
    required this.panelKind,
    required this.pendingApprovalCount,
    this.summary,
    this.focusAlert,
    this.selectedOperation,
    this.nextControlTask,
    this.computePolicy = const ComputeRolloutPolicy.empty(),
    this.computeActivity = const <ComputeGovernanceActivityEntry>[],
    this.pendingApprovalJobs = const <JobRecord>[],
    this.controlTasks = const <ControlTaskRecord>[],
    this.visibleControlTasks = const <ControlTaskRecord>[],
    this.activeAction,
    this.recentActions = const <ShellRuntimeActionState>[],
    this.notifications = const <ShellRuntimeNotification>[],
    this.operationSession = const ShellOperationSession.idle(),
    this.snapshotGeneratedAt,
    this.degradedSections = const <ShellRuntimeDegradedSection>[],
  });

  const MainShellProjection.empty()
    : activeTab = WorkbenchTab.operationsHub,
      activeTabLabel = '概览',
      panelVisible = false,
      panelKind = ShellRuntimePanelKind.approvals,
      pendingApprovalCount = 0,
      summary = null,
      focusAlert = null,
      selectedOperation = null,
      nextControlTask = null,
      computePolicy = const ComputeRolloutPolicy.empty(),
      computeActivity = const <ComputeGovernanceActivityEntry>[],
      pendingApprovalJobs = const <JobRecord>[],
      controlTasks = const <ControlTaskRecord>[],
      visibleControlTasks = const <ControlTaskRecord>[],
      activeAction = null,
      recentActions = const <ShellRuntimeActionState>[],
      notifications = const <ShellRuntimeNotification>[],
      operationSession = const ShellOperationSession.idle(),
      snapshotGeneratedAt = null,
      degradedSections = const <ShellRuntimeDegradedSection>[];

  final WorkbenchTab activeTab;
  final String activeTabLabel;
  final bool panelVisible;
  final ShellRuntimePanelKind panelKind;
  final int pendingApprovalCount;
  final DashboardSummary? summary;
  final DashboardAlert? focusAlert;
  final JobRecord? selectedOperation;
  final ControlTaskRecord? nextControlTask;
  final ComputeRolloutPolicy computePolicy;
  final List<ComputeGovernanceActivityEntry> computeActivity;
  final List<JobRecord> pendingApprovalJobs;
  final List<ControlTaskRecord> controlTasks;
  final List<ControlTaskRecord> visibleControlTasks;
  final ShellRuntimeActionState? activeAction;
  final List<ShellRuntimeActionState> recentActions;
  final List<ShellRuntimeNotification> notifications;
  final ShellOperationSession operationSession;
  final DateTime? snapshotGeneratedAt;
  final List<ShellRuntimeDegradedSection> degradedSections;

  bool get hasPendingApprovals => pendingApprovalCount > 0;
  bool get hasSelectedOperation => selectedOperation != null;
  bool get hasActiveAction => activeAction != null;
  bool get isDegraded => degradedSections.isNotEmpty;
  int get unreadNotificationCount =>
      notifications.where((item) => !item.isRead).length;

  String get selectedOperationLabel {
    final operation = selectedOperation;
    if (operation == null) {
      return '当前未选中运行';
    }
    return '${operation.displayTitle} · ${operation.status.toUpperCase()}';
  }

  String get nextControlTaskLabel {
    final task = nextControlTask;
    if (task == null) {
      return '当前没有待关注的规划任务';
    }
    final schedule = task.schedule?.trim();
    if (schedule == null || schedule.isEmpty) {
      return task.title;
    }
    return '${task.title} · $schedule';
  }

  String get activeActionLabel {
    final action = activeAction;
    if (action == null) {
      return '当前没有进行中的控制动作';
    }
    return '${action.intent.label} · ${action.phaseLabel}';
  }
}
