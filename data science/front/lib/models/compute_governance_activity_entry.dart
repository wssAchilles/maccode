/// Compute governance audit feed model.
library;

class ComputeGovernanceActivityEntry {
  const ComputeGovernanceActivityEntry({
    required this.entryId,
    required this.kind,
    required this.title,
    required this.status,
    required this.severity,
    required this.summary,
    required this.createdAt,
    required this.component,
    required this.componentLabel,
    required this.operationId,
    required this.operationType,
    required this.requestKind,
    required this.benchmarkStatus,
    required this.rolloutMode,
  });

  final String entryId;
  final String kind;
  final String title;
  final String status;
  final String severity;
  final String summary;
  final String createdAt;
  final String component;
  final String componentLabel;
  final String operationId;
  final String operationType;
  final String requestKind;
  final String benchmarkStatus;
  final String rolloutMode;

  bool get hasLinkedOperation => operationId.trim().isNotEmpty;
  bool get isSystemEvent => kind == 'system_event';

  factory ComputeGovernanceActivityEntry.fromJson(Map<String, dynamic> json) {
    return ComputeGovernanceActivityEntry(
      entryId: (json['entry_id'] ?? '').toString(),
      kind: (json['kind'] ?? 'operation').toString(),
      title: (json['title'] ?? '--').toString(),
      status: (json['status'] ?? '').toString(),
      severity: (json['severity'] ?? 'info').toString(),
      summary: (json['summary'] ?? '').toString(),
      createdAt: (json['created_at'] ?? '').toString(),
      component: (json['component'] ?? '').toString(),
      componentLabel: (json['component_label'] ?? '--').toString(),
      operationId: (json['operation_id'] ?? '').toString(),
      operationType: (json['operation_type'] ?? '').toString(),
      requestKind: (json['request_kind'] ?? '').toString(),
      benchmarkStatus: (json['benchmark_status'] ?? '').toString(),
      rolloutMode: (json['rollout_mode'] ?? '').toString(),
    );
  }
}
