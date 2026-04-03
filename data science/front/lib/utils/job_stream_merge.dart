/// 作业流式帧合并工具
library;

import '../models/job_record.dart';
import '../models/job_stream_frame.dart';

JobRecord mergeJobStreamFrame(JobRecord current, JobStreamFrame frame) {
  if (frame.isSnapshot) {
    return frame.snapshot ?? current;
  }

  if (frame.isState) {
    return _copyJob(
      current,
      status: frame.data['status']?.toString() ?? current.status,
      progress: _asInt(frame.data['progress']) ?? current.progress,
      currentStep: frame.data['current_step'] is Map<String, dynamic>
          ? JobStep.fromJson(frame.data['current_step'] as Map<String, dynamic>)
          : frame.data['current_step'] is Map
          ? JobStep.fromJson(Map<String, dynamic>.from(frame.data['current_step'] as Map))
          : current.currentStep,
      cancelRequested: _asBool(frame.data['cancel_requested']) ?? current.cancelRequested,
      approvalState: frame.data['approval_state'] is Map<String, dynamic>
          ? JobApprovalState.fromJson(frame.data['approval_state'] as Map<String, dynamic>)
          : frame.data['approval_state'] is Map
          ? JobApprovalState.fromJson(
              Map<String, dynamic>.from(frame.data['approval_state'] as Map),
            )
          : current.approvalState,
    );
  }

  if (frame.isClosed) {
    return _copyJob(
      current,
      status: frame.data['status']?.toString() ?? current.status,
      progress: frame.data['status']?.toString() == 'succeeded'
          ? 100
          : current.progress,
    );
  }

  final event = frame.jobEvent;
  if (event == null) {
    return current;
  }

  final nextEvents = _appendEvent(current.events, event);
  final nextStep = event.step ?? current.currentStep;
  final nextSteps = event.step == null
      ? current.steps
      : _upsertStep(current.steps, event.step!);
  final nextArtifacts = event.artifact == null
      ? current.artifacts
      : _appendArtifact(current.artifacts, event.artifact!);

  return _copyJob(
    current,
    status: _nextStatus(current.status, event.status),
    progress: event.progress,
    statusMessage: event.message.isEmpty ? current.statusMessage : event.message,
    currentStep: nextStep,
    steps: nextSteps,
    artifacts: nextArtifacts,
    events: nextEvents,
  );
}

JobRecord _copyJob(
  JobRecord source, {
  String? jobId,
  String? operationId,
  String? type,
  String? status,
  int? progress,
  String? requestedBy,
  int? attemptCount,
  int? maxAttempts,
  String? statusMessage,
  DateTime? submittedAt,
  DateTime? startedAt,
  DateTime? completedAt,
  Map<String, dynamic>? input,
  Map<String, dynamic>? result,
  JobError? error,
  bool? retryable,
  List<JobEvent>? events,
  String? controlTaskId,
  String? trigger,
  bool? cancelRequested,
  JobStep? currentStep,
  List<JobStep>? steps,
  List<JobArtifact>? artifacts,
  JobApprovalState? approvalState,
  Map<String, dynamic>? approvalPolicy,
  Map<String, dynamic>? metrics,
}) {
  return JobRecord(
    jobId: jobId ?? source.jobId,
    operationId: operationId ?? source.operationId,
    type: type ?? source.type,
    status: status ?? source.status,
    progress: progress ?? source.progress,
    requestedBy: requestedBy ?? source.requestedBy,
    attemptCount: attemptCount ?? source.attemptCount,
    maxAttempts: maxAttempts ?? source.maxAttempts,
    statusMessage: statusMessage ?? source.statusMessage,
    submittedAt: submittedAt ?? source.submittedAt,
    startedAt: startedAt ?? source.startedAt,
    completedAt: completedAt ?? source.completedAt,
    input: input ?? source.input,
    result: result ?? source.result,
    error: error ?? source.error,
    retryable: retryable ?? source.retryable,
    events: events ?? source.events,
    controlTaskId: controlTaskId ?? source.controlTaskId,
    trigger: trigger ?? source.trigger,
    cancelRequested: cancelRequested ?? source.cancelRequested,
    currentStep: currentStep ?? source.currentStep,
    steps: steps ?? source.steps,
    artifacts: artifacts ?? source.artifacts,
    approvalState: approvalState ?? source.approvalState,
    approvalPolicy: approvalPolicy ?? source.approvalPolicy,
    metrics: metrics ?? source.metrics,
  );
}

List<JobEvent> _appendEvent(List<JobEvent> events, JobEvent event) {
  final next = List<JobEvent>.from(events);
  final last = next.isEmpty ? null : next.last;
  if (last != null &&
      last.type == event.type &&
      last.phase == event.phase &&
      last.status == event.status &&
      last.message == event.message &&
      last.progress == event.progress) {
    return next;
  }
  next.add(event);
  return next;
}

List<JobArtifact> _appendArtifact(List<JobArtifact> artifacts, JobArtifact artifact) {
  final next = List<JobArtifact>.from(artifacts);
  final exists = next.any(
    (item) =>
        item.type == artifact.type &&
        item.name == artifact.name &&
        item.uri == artifact.uri,
  );
  if (!exists) {
    next.add(artifact);
  }
  return next;
}

List<JobStep> _upsertStep(List<JobStep> steps, JobStep step) {
  final next = <JobStep>[];
  var replaced = false;
  for (final existing in steps) {
    if (!replaced && existing.phase == step.phase) {
      next.add(step);
      replaced = true;
    } else {
      next.add(existing);
    }
  }
  if (!replaced) {
    next.add(step);
  }
  return next;
}

String _nextStatus(String currentStatus, String eventStatus) {
  if (eventStatus == 'ready') {
    return currentStatus;
  }
  return eventStatus.isEmpty ? currentStatus : eventStatus;
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
