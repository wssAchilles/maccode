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
  final DateTime? createdAt;
  final DateTime? updatedAt;

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
      createdAt: _parseDateTime(json['created_at']),
      updatedAt: _parseDateTime(json['updated_at']),
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
