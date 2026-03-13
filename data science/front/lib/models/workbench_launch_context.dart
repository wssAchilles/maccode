/// 工作台继续处理上下文
library;

class WorkbenchLaunchContext {
  const WorkbenchLaunchContext({
    required this.sourceLabel,
    required this.workspaceTarget,
    required this.workspaceTargetLabel,
    required this.cardTarget,
    required this.cardTargetLabel,
    required this.incidentTarget,
    required this.incidentTargetLabel,
    required this.workspaceBrief,
    required this.watchSummary,
  });

  final String sourceLabel;
  final String workspaceTarget;
  final String workspaceTargetLabel;
  final String cardTarget;
  final String cardTargetLabel;
  final String incidentTarget;
  final String incidentTargetLabel;
  final String workspaceBrief;
  final String watchSummary;
}
