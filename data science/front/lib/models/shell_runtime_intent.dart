library;

import 'workbench_runtime_models.dart';

enum ShellIntentDomain {
  workspace,
  approval,
  operation,
  controlTask,
  computeGovernance,
}

enum ShellIntentKind {
  openOperation,
  openPanel,
  resolveApproval,
  retryOperation,
  cancelOperation,
  runControlTask,
  updateControlTask,
  requestRolloutChange,
  requestBenchmark,
}

class ShellRuntimeIntent {
  const ShellRuntimeIntent({
    required this.id,
    required this.domain,
    required this.kind,
    required this.label,
    required this.sourceTab,
    required this.issuedAt,
    this.resourceId,
    this.resourceLabel,
    this.metadata = const <String, dynamic>{},
  });

  final String id;
  final ShellIntentDomain domain;
  final ShellIntentKind kind;
  final String label;
  final WorkbenchTab sourceTab;
  final DateTime issuedAt;
  final String? resourceId;
  final String? resourceLabel;
  final Map<String, dynamic> metadata;

  String get summary {
    final resourceLabel = this.resourceLabel?.trim();
    if (resourceLabel == null || resourceLabel.isEmpty) {
      return label;
    }
    return '$label · $resourceLabel';
  }
}
