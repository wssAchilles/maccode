/// 作业与审计模型
library;

import 'job_session_projection.dart';

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
    this.operationId,
    this.controlTaskId,
    this.trigger,
    this.executionTarget,
    this.cancelRequested = false,
    this.currentStep,
    this.steps = const <JobStep>[],
    this.artifacts = const <JobArtifact>[],
    this.approvalState,
    this.approvalPolicy,
    this.metrics = const <String, dynamic>{},
    this.sessionProjection,
  });

  final String jobId;
  final String? operationId;
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
  final String? controlTaskId;
  final String? trigger;
  final String? executionTarget;
  final Map<String, dynamic> input;
  final Map<String, dynamic> result;
  final JobError? error;
  final bool retryable;
  final bool cancelRequested;
  final JobStep? currentStep;
  final List<JobStep> steps;
  final List<JobArtifact> artifacts;
  final JobApprovalState? approvalState;
  final Map<String, dynamic>? approvalPolicy;
  final Map<String, dynamic> metrics;
  final List<JobEvent> events;
  final JobSessionProjection? sessionProjection;

  bool get isTerminal =>
      status == 'succeeded' || status == 'failed' || status == 'cancelled';

  bool get isRunning =>
      status == 'queued' ||
      status == 'dispatching' ||
      status == 'running' ||
      status == 'retrying';

  bool get requiresApproval => approvalState?.required == true;
  bool get isAwaitingApproval => approvalState?.state == 'pending';

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
      case 'fetch_data':
        return '小时数据抓取';
      case 'train_model':
        return '每日模型重训';
      case 'compute_rollout_change':
        return '计算治理变更';
      case 'compute_benchmark':
        return '计算基准验证';
      default:
        return type;
    }
  }

  factory JobRecord.fromJson(Map<String, dynamic> json) {
    final input = json['input'];
    final result = json['result'];
    final error = json['error'];
    final rawEvents = json['events'];
    final rawSteps = json['steps'];
    final rawArtifacts = json['artifacts'];
    final currentStep = json['current_step'];
    final approvalState = json['approval_state'];
    final sessionProjection = json['session_projection'];

    return JobRecord(
      jobId: (json['job_id'] ?? json['id'] ?? '').toString(),
      operationId: (json['operation_id'] ?? json['job_id'] ?? json['id'])
          ?.toString(),
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
      controlTaskId: json['control_task_id']?.toString(),
      trigger: json['trigger']?.toString(),
      executionTarget: json['execution_target']?.toString(),
      input: input is Map ? Map<String, dynamic>.from(input) : const {},
      result: result is Map ? Map<String, dynamic>.from(result) : const {},
      error: error is Map<String, dynamic>
          ? JobError.fromJson(error)
          : error is Map
          ? JobError.fromJson(Map<String, dynamic>.from(error))
          : null,
      retryable: _asBool(json['retryable']) ?? false,
      cancelRequested: _asBool(json['cancel_requested']) ?? false,
      currentStep: currentStep is Map<String, dynamic>
          ? JobStep.fromJson(currentStep)
          : currentStep is Map
          ? JobStep.fromJson(Map<String, dynamic>.from(currentStep))
          : null,
      steps: rawSteps is List
          ? rawSteps
                .map((item) {
                  if (item is Map<String, dynamic>) {
                    return JobStep.fromJson(item);
                  }
                  if (item is Map) {
                    return JobStep.fromJson(Map<String, dynamic>.from(item));
                  }
                  return null;
                })
                .whereType<JobStep>()
                .toList(growable: false)
          : const <JobStep>[],
      artifacts: rawArtifacts is List
          ? rawArtifacts
                .map((item) {
                  if (item is Map<String, dynamic>) {
                    return JobArtifact.fromJson(item);
                  }
                  if (item is Map) {
                    return JobArtifact.fromJson(
                      Map<String, dynamic>.from(item),
                    );
                  }
                  return null;
                })
                .whereType<JobArtifact>()
                .toList(growable: false)
          : const <JobArtifact>[],
      approvalState: approvalState is Map<String, dynamic>
          ? JobApprovalState.fromJson(approvalState)
          : approvalState is Map
          ? JobApprovalState.fromJson(Map<String, dynamic>.from(approvalState))
          : null,
      approvalPolicy: json['approval_policy'] is Map
          ? Map<String, dynamic>.from(json['approval_policy'] as Map)
          : null,
      metrics: json['metrics'] is Map
          ? Map<String, dynamic>.from(json['metrics'] as Map)
          : const <String, dynamic>{},
      sessionProjection: sessionProjection is Map<String, dynamic>
          ? JobSessionProjection.fromJson(sessionProjection)
          : sessionProjection is Map
          ? JobSessionProjection.fromJson(Map<String, dynamic>.from(sessionProjection))
          : null,
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

class JobStep {
  const JobStep({
    required this.phase,
    required this.toolName,
    required this.status,
    required this.progress,
    required this.message,
    this.startedAt,
    this.endedAt,
    this.durationMs,
    this.executionTarget,
    this.timeoutS,
    this.retryPolicy,
    this.approvalPolicy,
    this.artifactPolicy,
    this.concurrencyKey,
    this.metrics = const <String, dynamic>{},
  });

  final String phase;
  final String toolName;
  final String status;
  final int progress;
  final String message;
  final DateTime? startedAt;
  final DateTime? endedAt;
  final int? durationMs;
  final String? executionTarget;
  final int? timeoutS;
  final Map<String, dynamic>? retryPolicy;
  final Map<String, dynamic>? approvalPolicy;
  final Map<String, dynamic>? artifactPolicy;
  final String? concurrencyKey;
  final Map<String, dynamic> metrics;

  factory JobStep.fromJson(Map<String, dynamic> json) {
    return JobStep(
      phase: (json['phase'] ?? 'progress').toString(),
      toolName: (json['tool_name'] ?? json['phase'] ?? 'unknown').toString(),
      status: (json['status'] ?? 'running').toString(),
      progress: _asInt(json['progress']) ?? 0,
      message: (json['message'] ?? '').toString(),
      startedAt: _parseDateTime(json['started_at']),
      endedAt: _parseDateTime(json['ended_at']),
      durationMs: _asInt(json['duration_ms']),
      executionTarget: json['execution_target']?.toString(),
      timeoutS: _asInt(json['timeout_s']),
      retryPolicy: json['retry_policy'] is Map
          ? Map<String, dynamic>.from(json['retry_policy'] as Map)
          : null,
      approvalPolicy: json['approval_policy'] is Map
          ? Map<String, dynamic>.from(json['approval_policy'] as Map)
          : null,
      artifactPolicy: json['artifact_policy'] is Map
          ? Map<String, dynamic>.from(json['artifact_policy'] as Map)
          : null,
      concurrencyKey: json['concurrency_key']?.toString(),
      metrics: json['metrics'] is Map
          ? Map<String, dynamic>.from(json['metrics'] as Map)
          : const <String, dynamic>{},
    );
  }
}

class JobEvent {
  const JobEvent({
    this.type = 'step.progress',
    required this.phase,
    required this.status,
    required this.message,
    required this.progress,
    this.timestamp,
    this.step,
    this.artifact,
    this.metrics = const <String, dynamic>{},
  });

  final String type;
  final String phase;
  final String status;
  final String message;
  final int progress;
  final DateTime? timestamp;
  final JobStep? step;
  final JobArtifact? artifact;
  final Map<String, dynamic> metrics;

  factory JobEvent.fromJson(Map<String, dynamic> json) {
    return JobEvent(
      type: (json['type'] ?? 'step.progress').toString(),
      phase: (json['phase'] ?? 'progress').toString(),
      status: (json['status'] ?? 'running').toString(),
      message: (json['message'] ?? '').toString(),
      progress: _asInt(json['progress']) ?? 0,
      timestamp: _parseDateTime(json['timestamp']),
      step: json['step'] is Map<String, dynamic>
          ? JobStep.fromJson(json['step'] as Map<String, dynamic>)
          : json['step'] is Map
          ? JobStep.fromJson(Map<String, dynamic>.from(json['step'] as Map))
          : null,
      artifact: json['artifact'] is Map<String, dynamic>
          ? JobArtifact.fromJson(json['artifact'] as Map<String, dynamic>)
          : json['artifact'] is Map
          ? JobArtifact.fromJson(
              Map<String, dynamic>.from(json['artifact'] as Map),
            )
          : null,
      metrics: json['metrics'] is Map
          ? Map<String, dynamic>.from(json['metrics'] as Map)
          : const <String, dynamic>{},
    );
  }
}

class JobArtifact {
  const JobArtifact({
    required this.type,
    required this.name,
    this.uri,
    this.status,
    this.metadata = const <String, dynamic>{},
    this.createdAt,
  });

  final String type;
  final String name;
  final String? uri;
  final String? status;
  final Map<String, dynamic> metadata;
  final DateTime? createdAt;

  factory JobArtifact.fromJson(Map<String, dynamic> json) {
    return JobArtifact(
      type: (json['type'] ?? 'artifact').toString(),
      name: (json['name'] ?? 'Artifact').toString(),
      uri: json['uri']?.toString(),
      status: json['status']?.toString(),
      metadata: json['metadata'] is Map
          ? Map<String, dynamic>.from(json['metadata'] as Map)
          : const <String, dynamic>{},
      createdAt: _parseDateTime(json['created_at']),
    );
  }
}

class JobApprovalState {
  const JobApprovalState({
    required this.required,
    required this.state,
    this.reason,
    this.approvedBy,
    this.approvedAt,
    this.message,
  });

  final bool required;
  final String state;
  final String? reason;
  final String? approvedBy;
  final DateTime? approvedAt;
  final String? message;

  factory JobApprovalState.fromJson(Map<String, dynamic> json) {
    return JobApprovalState(
      required: _asBool(json['required']) ?? false,
      state: (json['state'] ?? 'not_required').toString(),
      reason: json['reason']?.toString(),
      approvedBy: json['approved_by']?.toString(),
      approvedAt: _parseDateTime(json['approved_at']),
      message: json['message']?.toString(),
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
