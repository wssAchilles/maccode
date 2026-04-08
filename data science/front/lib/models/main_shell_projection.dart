library;

import 'control_task_record.dart';
import 'dashboard_summary.dart';
import 'job_record.dart';
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
    this.pendingApprovalJobs = const <JobRecord>[],
    this.visibleControlTasks = const <ControlTaskRecord>[],
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
      pendingApprovalJobs = const <JobRecord>[],
      visibleControlTasks = const <ControlTaskRecord>[];

  final WorkbenchTab activeTab;
  final String activeTabLabel;
  final bool panelVisible;
  final ShellRuntimePanelKind panelKind;
  final int pendingApprovalCount;
  final DashboardSummary? summary;
  final DashboardAlert? focusAlert;
  final JobRecord? selectedOperation;
  final ControlTaskRecord? nextControlTask;
  final List<JobRecord> pendingApprovalJobs;
  final List<ControlTaskRecord> visibleControlTasks;

  bool get hasPendingApprovals => pendingApprovalCount > 0;
  bool get hasSelectedOperation => selectedOperation != null;

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
}
