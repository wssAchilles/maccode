/// 作业与审计模型
library;

class JobRecord {
  const JobRecord({
    required this.jobId,
    required this.type,
    required this.status,
    required this.progress,
    required this.requestedBy,
    required this.attemptCount,
    required this.maxAttempts,
    this.statusMessage,
    this.submittedAt,
    this.startedAt,
    this.completedAt,
    this.input = const <String, dynamic>{},
    this.result = const <String, dynamic>{},
    this.error,
    this.retryable = false,
    this.events = const <JobEvent>[],
  });

  final String jobId;
  final String type;
  final String status;
  final int progress;
  final String requestedBy;
  final int attemptCount;
  final int maxAttempts;
  final String? statusMessage;
  final DateTime? submittedAt;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final Map<String, dynamic> input;
  final Map<String, dynamic> result;
  final JobError? error;
  final bool retryable;
  final List<JobEvent> events;

  bool get isTerminal =>
      status == 'succeeded' || status == 'failed' || status == 'cancelled';

  bool get isRunning => status == 'queued' || status == 'running';

  JobEvent? get latestEvent => events.isEmpty ? null : events.last;

  String get displayTitle {
    switch (type) {
      case 'analysis':
        return '数据分析';
      case 'optimization':
        return '能源优化';
      case 'ml_train':
        return '深度学习训练';
      case 'rag_ingest':
        return '知识库构建';
      default:
        return type;
    }
  }

  factory JobRecord.fromJson(Map<String, dynamic> json) {
    final input = json['input'];
    final result = json['result'];
    final error = json['error'];
    final rawEvents = json['events'];

    return JobRecord(
      jobId: (json['job_id'] ?? json['id'] ?? '').toString(),
      type: (json['type'] ?? 'unknown').toString(),
      status: (json['status'] ?? 'queued').toString(),
      progress: _asInt(json['progress']) ?? 0,
      requestedBy: (json['requested_by'] ?? '').toString(),
      attemptCount: _asInt(json['attempt_count']) ?? 0,
      maxAttempts: _asInt(json['max_attempts']) ?? 1,
      statusMessage: json['status_message']?.toString(),
      submittedAt: _parseDateTime(json['submitted_at']),
      startedAt: _parseDateTime(json['started_at']),
      completedAt: _parseDateTime(json['completed_at']),
      input: input is Map ? Map<String, dynamic>.from(input) : const {},
      result: result is Map ? Map<String, dynamic>.from(result) : const {},
      error: error is Map<String, dynamic>
          ? JobError.fromJson(error)
          : error is Map
          ? JobError.fromJson(Map<String, dynamic>.from(error))
          : null,
      retryable: _asBool(json['retryable']) ?? false,
      events: rawEvents is List
          ? rawEvents
                .map((item) {
                  if (item is Map<String, dynamic>) {
                    return JobEvent.fromJson(item);
                  }
                  if (item is Map) {
                    return JobEvent.fromJson(Map<String, dynamic>.from(item));
                  }
                  return null;
                })
                .whereType<JobEvent>()
                .toList(growable: false)
          : const <JobEvent>[],
    );
  }
}

class JobEvent {
  const JobEvent({
    required this.phase,
    required this.status,
    required this.message,
    required this.progress,
    this.timestamp,
  });

  final String phase;
  final String status;
  final String message;
  final int progress;
  final DateTime? timestamp;

  factory JobEvent.fromJson(Map<String, dynamic> json) {
    return JobEvent(
      phase: (json['phase'] ?? 'progress').toString(),
      status: (json['status'] ?? 'running').toString(),
      message: (json['message'] ?? '').toString(),
      progress: _asInt(json['progress']) ?? 0,
      timestamp: _parseDateTime(json['timestamp']),
    );
  }
}

class JobError {
  const JobError({required this.code, required this.message, this.details});

  final String code;
  final String message;
  final Object? details;

  factory JobError.fromJson(Map<String, dynamic> json) {
    return JobError(
      code: (json['code'] ?? 'UNKNOWN').toString(),
      message: (json['message'] ?? '未知错误').toString(),
      details: json['details'],
    );
  }
}

class AuditActivity {
  const AuditActivity({
    required this.id,
    required this.action,
    required this.status,
    required this.source,
    required this.severity,
    required this.title,
    required this.details,
    this.resourceType,
    this.resourceId,
    this.createdAt,
  });

  final String id;
  final String action;
  final String status;
  final String source;
  final String severity;
  final String title;
  final Map<String, dynamic> details;
  final String? resourceType;
  final String? resourceId;
  final DateTime? createdAt;

  factory AuditActivity.fromJson(Map<String, dynamic> json) {
    final details = json['details'];
    return AuditActivity(
      id: (json['id'] ?? '').toString(),
      action: (json['action'] ?? 'unknown').toString(),
      status: (json['status'] ?? 'unknown').toString(),
      source: (json['source'] ?? 'system').toString(),
      severity: (json['severity'] ?? 'info').toString(),
      title: (json['title'] ?? json['action'] ?? '活动').toString(),
      details: details is Map ? Map<String, dynamic>.from(details) : const {},
      resourceType: json['resource_type']?.toString(),
      resourceId: json['resource_id']?.toString(),
      createdAt: _parseDateTime(json['created_at']),
    );
  }
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
