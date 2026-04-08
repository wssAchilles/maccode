library;

import '../models/control_task_record.dart';
import '../models/compute_governance_activity_entry.dart';
import '../models/compute_rollout_policy.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../models/main_shell_projection.dart';
import '../models/shell_operation_session.dart';
import '../models/shell_runtime_action_state.dart';
import '../models/shell_runtime_notification.dart';
import '../models/workbench_runtime_models.dart';

MainShellProjection buildMainShellProjection({
  required WorkbenchTab activeTab,
  required bool panelVisible,
  required ShellRuntimePanelKind panelKind,
  required DashboardSummary? summary,
  required List<JobRecord> approvalJobs,
  required List<ControlTaskRecord> controlTasks,
  required ComputeRolloutPolicy computePolicy,
  required List<ComputeGovernanceActivityEntry> computeActivity,
  required JobRecord? selectedOperation,
  required ShellRuntimeActionState? activeAction,
  required List<ShellRuntimeActionState> recentActions,
  required List<ShellRuntimeNotification> notifications,
  required ShellOperationSession operationSession,
}) {
  final sortedAlerts = [...?summary?.alerts]..sort(_compareAlertPriority);
  final focusAlert = sortedAlerts.isEmpty ? null : sortedAlerts.first;
  final visibleControlTasks = [...controlTasks]
    ..sort(_compareControlTaskPriority);

  return MainShellProjection(
    activeTab: activeTab,
    activeTabLabel: _activeTabLabel(activeTab),
    panelVisible: panelVisible,
    panelKind: panelKind,
    pendingApprovalCount: approvalJobs.length,
    summary: summary,
    focusAlert: focusAlert,
    selectedOperation: selectedOperation,
    nextControlTask: visibleControlTasks.isEmpty ? null : visibleControlTasks.first,
    computePolicy: computePolicy,
    computeActivity: computeActivity,
    pendingApprovalJobs: approvalJobs,
    controlTasks: controlTasks,
    visibleControlTasks: visibleControlTasks.take(4).toList(growable: false),
    activeAction: activeAction,
    recentActions: recentActions,
    notifications: notifications,
    operationSession: operationSession,
  );
}

int _compareAlertPriority(DashboardAlert left, DashboardAlert right) {
  return _alertPriority(right.severity).compareTo(_alertPriority(left.severity));
}

int _alertPriority(String severity) {
  switch (severity) {
    case 'critical':
      return 4;
    case 'error':
      return 3;
    case 'warning':
      return 2;
    case 'success':
      return 1;
    default:
      return 0;
  }
}

int _compareControlTaskPriority(
  ControlTaskRecord left,
  ControlTaskRecord right,
) {
  final leftPriority = _controlTaskPriority(left);
  final rightPriority = _controlTaskPriority(right);
  if (leftPriority != rightPriority) {
    return rightPriority.compareTo(leftPriority);
  }

  final leftNext = left.nextRunAt?.millisecondsSinceEpoch ?? 1 << 30;
  final rightNext = right.nextRunAt?.millisecondsSinceEpoch ?? 1 << 30;
  return leftNext.compareTo(rightNext);
}

int _controlTaskPriority(ControlTaskRecord task) {
  if (!task.enabled) {
    return 0;
  }
  if (task.isDependencyBlocked) {
    return 1;
  }
  if (task.latestOperation?.status == 'running') {
    return 4;
  }
  if (task.latestOperation?.status == 'awaiting_approval') {
    return 3;
  }
  return 2;
}

String _activeTabLabel(WorkbenchTab tab) {
  switch (tab) {
    case WorkbenchTab.operationsHub:
      return '概览';
    case WorkbenchTab.modeling:
      return '能源优化';
    case WorkbenchTab.dataAnalysis:
      return '数据分析';
    case WorkbenchTab.aiLab:
      return 'AI Lab';
    case WorkbenchTab.historyAudit:
      return '历史与审计';
  }
}
