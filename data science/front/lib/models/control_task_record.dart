/// 规划任务读模型
library;

class ControlTaskRecord {
  const ControlTaskRecord({
    required this.id,
    required this.kind,
    this.operationType = '',
    required this.title,
    this.schedule,
    this.defaultInput = const <String, dynamic>{},
    this.dependencies = const <String>[],
    this.approvalPolicy = const <String, dynamic>{},
    this.enabled = true,
    this.owner = '',
    this.nextRunAt,
    this.dependencyState = '',
    this.dependencySummary = '',
    this.dependencyDetails = const <ControlTaskDependencyDetail>[],
    this.latestOperation,
    this.createdAt,
    this.updatedAt,
  });

  final String id;
  final String kind;
  final String operationType;
  final String title;
  final String? schedule;
  final Map<String, dynamic> defaultInput;
  final List<String> dependencies;
  final Map<String, dynamic> approvalPolicy;
  final bool enabled;
  final String owner;
  final DateTime? nextRunAt;
  final String dependencyState;
  final String dependencySummary;
  final List<ControlTaskDependencyDetail> dependencyDetails;
  final ControlTaskLatestOperation? latestOperation;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  bool get canRunByDependency =>
      dependencyState.isEmpty ||
      dependencyState == 'none' ||
      dependencyState == 'ready';

  bool get isDependencyBlocked =>
      dependencyState == 'blocked' || dependencyState == 'missing';

  String get dependencyGateMessage {
    if (dependencyState == 'missing') {
      return dependencySummary.isEmpty ? '存在未定义依赖' : dependencySummary;
    }
    if (dependencyState == 'blocked') {
      return dependencySummary.isEmpty ? '存在已暂停依赖' : dependencySummary;
    }
    return '依赖已就绪';
  }

  ControlTaskRecord copyWith({
    String? id,
    String? kind,
    String? operationType,
    String? title,
    String? schedule,
    Map<String, dynamic>? defaultInput,
    List<String>? dependencies,
    Map<String, dynamic>? approvalPolicy,
    bool? enabled,
    String? owner,
    DateTime? nextRunAt,
    String? dependencyState,
    String? dependencySummary,
    List<ControlTaskDependencyDetail>? dependencyDetails,
    ControlTaskLatestOperation? latestOperation,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return ControlTaskRecord(
      id: id ?? this.id,
      kind: kind ?? this.kind,
      operationType: operationType ?? this.operationType,
      title: title ?? this.title,
      schedule: schedule ?? this.schedule,
      defaultInput: defaultInput ?? this.defaultInput,
      dependencies: dependencies ?? this.dependencies,
      approvalPolicy: approvalPolicy ?? this.approvalPolicy,
      enabled: enabled ?? this.enabled,
      owner: owner ?? this.owner,
      nextRunAt: nextRunAt ?? this.nextRunAt,
      dependencyState: dependencyState ?? this.dependencyState,
      dependencySummary: dependencySummary ?? this.dependencySummary,
      dependencyDetails: dependencyDetails ?? this.dependencyDetails,
      latestOperation: latestOperation ?? this.latestOperation,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  factory ControlTaskRecord.fromJson(Map<String, dynamic> json) {
    return ControlTaskRecord(
      id: (json['id'] ?? '').toString(),
      kind: (json['kind'] ?? '').toString(),
      operationType: (json['operation_type'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      schedule: json['schedule']?.toString(),
      defaultInput: json['default_input'] is Map
          ? Map<String, dynamic>.from(json['default_input'] as Map)
          : const <String, dynamic>{},
      dependencies: (json['dependencies'] is List)
          ? (json['dependencies'] as List)
                .map((item) => item.toString())
                .toList(growable: false)
          : const <String>[],
      approvalPolicy: json['approval_policy'] is Map
          ? Map<String, dynamic>.from(json['approval_policy'] as Map)
          : const <String, dynamic>{},
      enabled: _asBool(json['enabled']) ?? true,
      owner: (json['owner'] ?? '').toString(),
      nextRunAt: _parseDateTime(json['next_run_at']),
      dependencyState: (json['dependency_state'] ?? '').toString(),
      dependencySummary: (json['dependency_summary'] ?? '').toString(),
      dependencyDetails: (json['dependency_details'] is List)
          ? (json['dependency_details'] as List)
                .map((item) {
                  if (item is Map<String, dynamic>) {
                    return ControlTaskDependencyDetail.fromJson(item);
                  }
                  if (item is Map) {
                    return ControlTaskDependencyDetail.fromJson(
                      Map<String, dynamic>.from(item),
                    );
                  }
                  return null;
                })
                .whereType<ControlTaskDependencyDetail>()
                .toList(growable: false)
          : const <ControlTaskDependencyDetail>[],
      latestOperation: json['latest_operation'] is Map<String, dynamic>
          ? ControlTaskLatestOperation.fromJson(json['latest_operation'])
          : json['latest_operation'] is Map
          ? ControlTaskLatestOperation.fromJson(
              Map<String, dynamic>.from(json['latest_operation']),
            )
          : null,
      createdAt: _parseDateTime(json['created_at']),
      updatedAt: _parseDateTime(json['updated_at']),
    );
  }
}

class ControlTaskDependencyDetail {
  const ControlTaskDependencyDetail({
    required this.id,
    required this.state,
    required this.title,
  });

  final String id;
  final String state;
  final String title;

  factory ControlTaskDependencyDetail.fromJson(Map<String, dynamic> json) {
    return ControlTaskDependencyDetail(
      id: (json['id'] ?? '').toString(),
      state: (json['state'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
    );
  }
}

class ControlTaskLatestOperation {
  const ControlTaskLatestOperation({
    required this.operationId,
    required this.type,
    required this.status,
    required this.progress,
    this.submittedAt,
  });

  final String operationId;
  final String type;
  final String status;
  final int progress;
  final DateTime? submittedAt;

  factory ControlTaskLatestOperation.fromJson(Map<String, dynamic> json) {
    return ControlTaskLatestOperation(
      operationId: (json['operation_id'] ?? json['job_id'] ?? json['id'] ?? '')
          .toString(),
      type: (json['type'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      progress: _asInt(json['progress']) ?? 0,
      submittedAt: _parseDateTime(json['submitted_at']),
    );
  }
}

DateTime? _parseDateTime(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  if (value is String && value.isNotEmpty) {
    return DateTime.tryParse(value);
  }
  return null;
}

bool? _asBool(Object? value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    final normalized = value.toLowerCase();
    if (normalized == 'true' || normalized == '1') {
      return true;
    }
    if (normalized == 'false' || normalized == '0') {
      return false;
    }
  }
  return null;
}

int? _asInt(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value);
  }
  return null;
}
