/// Compute rollout governance model.
library;

class ComputeRolloutPolicy {
  const ComputeRolloutPolicy({
    required this.enabled,
    required this.updatedAt,
    required this.updatedBy,
    this.guardEnabled = false,
    this.guardFailureThreshold = 0,
    this.guardWindowMinutes = 0,
    this.runtimeTargets = const <ComputeRuntimeTargetStatus>[],
    this.components = const <ComputeRolloutComponentPolicy>[],
  });

  const ComputeRolloutPolicy.empty()
      : enabled = false,
      updatedAt = '',
      updatedBy = '',
      guardEnabled = false,
      guardFailureThreshold = 0,
      guardWindowMinutes = 0,
      runtimeTargets = const <ComputeRuntimeTargetStatus>[],
      components = const <ComputeRolloutComponentPolicy>[];

  final bool enabled;
  final String updatedAt;
  final String updatedBy;
  final bool guardEnabled;
  final int guardFailureThreshold;
  final int guardWindowMinutes;
  final List<ComputeRuntimeTargetStatus> runtimeTargets;
  final List<ComputeRolloutComponentPolicy> components;

  factory ComputeRolloutPolicy.fromJson(Map<String, dynamic> json) {
    return ComputeRolloutPolicy(
      enabled: _asBool(json['enabled']) ?? false,
      updatedAt: (json['updated_at'] ?? '').toString(),
      updatedBy: (json['updated_by'] ?? '').toString(),
      guardEnabled: _asBool(json['guard_enabled']) ?? false,
      guardFailureThreshold: _asInt(json['guard_failure_threshold']) ?? 0,
      guardWindowMinutes: _asInt(json['guard_window_minutes']) ?? 0,
      runtimeTargets: _mapList(
        json['runtime_targets'],
        ComputeRuntimeTargetStatus.fromJson,
      ),
      components: _mapList(
        json['components'],
        ComputeRolloutComponentPolicy.fromJson,
      ),
    );
  }
}

class ComputeRuntimeTargetStatus {
  const ComputeRuntimeTargetStatus({
    required this.workerKey,
    required this.workerLabel,
    required this.configured,
    required this.reachable,
    required this.nativeEnabled,
    required this.nativeAvailable,
    required this.preferredBackend,
    required this.activeBackend,
    required this.statusReason,
  });

  final String workerKey;
  final String workerLabel;
  final bool configured;
  final bool reachable;
  final bool nativeEnabled;
  final bool nativeAvailable;
  final String preferredBackend;
  final String activeBackend;
  final String statusReason;

  factory ComputeRuntimeTargetStatus.fromJson(Map<String, dynamic> json) {
    return ComputeRuntimeTargetStatus(
      workerKey: (json['worker_key'] ?? '').toString(),
      workerLabel: (json['worker_label'] ?? '--').toString(),
      configured: _asBool(json['configured']) ?? false,
      reachable: _asBool(json['reachable']) ?? false,
      nativeEnabled: _asBool(json['native_enabled']) ?? false,
      nativeAvailable: _asBool(json['native_available']) ?? false,
      preferredBackend: (json['preferred_backend'] ?? 'python_pandas')
          .toString(),
      activeBackend: (json['active_backend'] ?? 'python_pandas').toString(),
      statusReason: (json['status_reason'] ?? '').toString(),
    );
  }
}

class ComputeRolloutComponentPolicy {
  const ComputeRolloutComponentPolicy({
    required this.key,
    required this.label,
    required this.rolloutMode,
    required this.preferredBackend,
    required this.canaryPercent,
    required this.requireBenchmark,
    required this.lastBenchmarkAt,
    required this.lastBenchmarkContext,
    required this.lastBenchmarkBackend,
    required this.benchmarkStatus,
    required this.benchmarkPassed,
    required this.benchmarkSummary,
    required this.benchmarkThreshold,
    this.benchmarkSpeedupRatio,
    this.benchmarkSampleRows = 0,
    this.benchmarkStale = false,
    required this.notes,
    required this.rolloutStatus,
    required this.rolloutBlocker,
    required this.guardEnabled,
    required this.guardFailureThreshold,
    required this.guardWindowMinutes,
    required this.recentFailureCount,
    required this.lastFailureAt,
    required this.lastFailureReason,
    required this.lastFailureContext,
    required this.lastSuccessAt,
    required this.autoRollbackCount,
    required this.lastAutoRollbackAt,
    required this.lastAutoRollbackReason,
    required this.lastAutoRollbackTo,
    this.nativeReadyTargets = const <String>[],
    this.runtimeTargets = const <ComputeRuntimeTargetStatus>[],
    this.allowedBackends = const <String>[],
    this.allowedModes = const <String>[],
  });

  final String key;
  final String label;
  final String rolloutMode;
  final String preferredBackend;
  final int canaryPercent;
  final bool requireBenchmark;
  final String lastBenchmarkAt;
  final String lastBenchmarkContext;
  final String lastBenchmarkBackend;
  final String benchmarkStatus;
  final bool benchmarkPassed;
  final String benchmarkSummary;
  final double benchmarkThreshold;
  final double? benchmarkSpeedupRatio;
  final int benchmarkSampleRows;
  final bool benchmarkStale;
  final String notes;
  final String rolloutStatus;
  final String rolloutBlocker;
  final bool guardEnabled;
  final int guardFailureThreshold;
  final int guardWindowMinutes;
  final int recentFailureCount;
  final String lastFailureAt;
  final String lastFailureReason;
  final String lastFailureContext;
  final String lastSuccessAt;
  final int autoRollbackCount;
  final String lastAutoRollbackAt;
  final String lastAutoRollbackReason;
  final String lastAutoRollbackTo;
  final List<String> nativeReadyTargets;
  final List<ComputeRuntimeTargetStatus> runtimeTargets;
  final List<String> allowedBackends;
  final List<String> allowedModes;

  bool get benchmarkReady => benchmarkPassed;

  factory ComputeRolloutComponentPolicy.fromJson(Map<String, dynamic> json) {
    return ComputeRolloutComponentPolicy(
      key: (json['key'] ?? '').toString(),
      label: (json['label'] ?? '--').toString(),
      rolloutMode: (json['rollout_mode'] ?? 'python_stable').toString(),
      preferredBackend: (json['preferred_backend'] ?? 'python_pandas')
          .toString(),
      canaryPercent: _asInt(json['canary_percent']) ?? 0,
      requireBenchmark: _asBool(json['require_benchmark']) ?? false,
      lastBenchmarkAt: (json['last_benchmark_at'] ?? '').toString(),
      lastBenchmarkContext: (json['last_benchmark_context'] ?? '').toString(),
      lastBenchmarkBackend: (json['last_benchmark_backend'] ?? '').toString(),
      benchmarkStatus: (json['benchmark_status'] ?? 'pending').toString(),
      benchmarkPassed: _asBool(json['benchmark_passed']) ?? false,
      benchmarkSummary: (json['benchmark_summary'] ?? '').toString(),
      benchmarkThreshold: _asDouble(json['benchmark_threshold']) ?? 0,
      benchmarkSpeedupRatio: _asDouble(json['benchmark_speedup_ratio']),
      benchmarkSampleRows: _asInt(json['benchmark_sample_rows']) ?? 0,
      benchmarkStale: _asBool(json['benchmark_stale']) ?? false,
      notes: (json['notes'] ?? '').toString(),
      rolloutStatus: (json['rollout_status'] ?? 'stable').toString(),
      rolloutBlocker: (json['rollout_blocker'] ?? '').toString(),
      guardEnabled: _asBool(json['guard_enabled']) ?? false,
      guardFailureThreshold: _asInt(json['guard_failure_threshold']) ?? 0,
      guardWindowMinutes: _asInt(json['guard_window_minutes']) ?? 0,
      recentFailureCount: _asInt(json['recent_failure_count']) ?? 0,
      lastFailureAt: (json['last_failure_at'] ?? '').toString(),
      lastFailureReason: (json['last_failure_reason'] ?? '').toString(),
      lastFailureContext: (json['last_failure_context'] ?? '').toString(),
      lastSuccessAt: (json['last_success_at'] ?? '').toString(),
      autoRollbackCount: _asInt(json['auto_rollback_count']) ?? 0,
      lastAutoRollbackAt: (json['last_auto_rollback_at'] ?? '').toString(),
      lastAutoRollbackReason: (json['last_auto_rollback_reason'] ?? '')
          .toString(),
      lastAutoRollbackTo: (json['last_auto_rollback_to'] ?? '').toString(),
      nativeReadyTargets: _mapPrimitiveList(json['native_ready_targets']),
      runtimeTargets: _mapList(
        json['runtime_targets'],
        ComputeRuntimeTargetStatus.fromJson,
      ),
      allowedBackends: _mapPrimitiveList(json['allowed_backends']),
      allowedModes: _mapPrimitiveList(json['allowed_modes']),
    );
  }
}

List<T> _mapList<T>(Object? payload, T Function(Map<String, dynamic>) parser) {
  if (payload is! List) {
    return <T>[];
  }
  return payload
      .whereType<Map>()
      .map((item) => parser(Map<String, dynamic>.from(item)))
      .toList(growable: false);
}

List<String> _mapPrimitiveList(Object? payload) {
  if (payload is! List) {
    return const <String>[];
  }
  return payload.map((item) => item.toString()).toList(growable: false);
}

bool? _asBool(Object? value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    if (value == 'true' || value == '1') {
      return true;
    }
    if (value == 'false' || value == '0') {
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

double? _asDouble(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}
