/// Helpers for operation-level compute telemetry rendering.
library;

class OperationComputeMetric {
  const OperationComputeMetric({
    required this.key,
    required this.label,
    required this.backend,
    required this.rolloutMode,
    required this.rolloutReason,
    required this.fallbackReason,
    required this.durationMs,
    required this.rows,
    required this.context,
    required this.nativeEnabled,
    required this.nativeAvailable,
    required this.benchmarkReady,
    required this.benchmarkStatus,
    required this.benchmarkSummary,
    required this.benchmarkSpeedupRatio,
    required this.guardRecentFailureCount,
    required this.guardFailureThreshold,
    required this.guardWindowMinutes,
    required this.guardAutoRollbackApplied,
    required this.guardLastAutoRollbackAt,
    required this.guardLastAutoRollbackReason,
  });

  final String key;
  final String label;
  final String backend;
  final String rolloutMode;
  final String rolloutReason;
  final String fallbackReason;
  final double durationMs;
  final int rows;
  final String context;
  final bool nativeEnabled;
  final bool nativeAvailable;
  final bool benchmarkReady;
  final String benchmarkStatus;
  final String benchmarkSummary;
  final double? benchmarkSpeedupRatio;
  final int guardRecentFailureCount;
  final int guardFailureThreshold;
  final int guardWindowMinutes;
  final bool guardAutoRollbackApplied;
  final String guardLastAutoRollbackAt;
  final String guardLastAutoRollbackReason;
}

List<OperationComputeMetric> extractOperationComputeMetrics(
  Map<String, dynamic> metrics,
) {
  final raw = metrics['compute_metrics'];
  if (raw is! Map) {
    return const <OperationComputeMetric>[];
  }

  return raw.entries.map((entry) {
    final payload = entry.value is Map
        ? Map<String, dynamic>.from(entry.value as Map)
        : const <String, dynamic>{};
    return OperationComputeMetric(
      key: entry.key.toString(),
      label: (payload['label'] ?? _defaultLabel(entry.key.toString())).toString(),
      backend: (payload['backend'] ?? 'python_pandas').toString(),
      rolloutMode: (payload['rollout_mode'] ?? '').toString(),
      rolloutReason: (payload['rollout_reason'] ?? '').toString(),
      fallbackReason: (payload['fallback_reason'] ?? '').toString(),
      durationMs: _asDouble(payload['duration_ms']) ?? 0,
      rows: _asInt(payload['rows']) ?? 0,
      context: (payload['context'] ?? '').toString(),
      nativeEnabled: _asBool(payload['native_enabled']) ?? false,
      nativeAvailable: _asBool(payload['native_available']) ?? false,
      benchmarkReady: _asBool(payload['benchmark_ready']) ?? false,
      benchmarkStatus: (payload['benchmark_status'] ?? '').toString(),
      benchmarkSummary: (payload['benchmark_summary'] ?? '').toString(),
      benchmarkSpeedupRatio: _asDouble(payload['benchmark_speedup_ratio']),
      guardRecentFailureCount: _asInt(payload['guard_recent_failure_count']) ?? 0,
      guardFailureThreshold: _asInt(payload['guard_failure_threshold']) ?? 0,
      guardWindowMinutes: _asInt(payload['guard_window_minutes']) ?? 0,
      guardAutoRollbackApplied:
          _asBool(payload['guard_auto_rollback_applied']) ?? false,
      guardLastAutoRollbackAt:
          (payload['guard_last_auto_rollback_at'] ?? '').toString(),
      guardLastAutoRollbackReason:
          (payload['guard_last_auto_rollback_reason'] ?? '').toString(),
    );
  }).toList(growable: false);
}

String buildComputeSummaryLine(Map<String, dynamic> metrics) {
  final items = extractOperationComputeMetrics(metrics);
  if (items.isEmpty) {
    return '';
  }
  final lead = items.first;
  final suffix = items.length > 1 ? ' +${items.length - 1}' : '';
  final context = lead.context.isEmpty ? '' : ' · ${lead.context}';
  final rollout = lead.rolloutMode.isEmpty ? '' : ' · ${lead.rolloutMode}';
  final fallback = lead.fallbackReason.isEmpty ? '' : ' · fallback';
  return '${lead.label} · ${lead.durationMs.toStringAsFixed(1)}ms · ${lead.backend}$rollout$context$fallback$suffix';
}

String _defaultLabel(String key) {
  switch (key) {
    case 'feature_engineering':
      return '高级特征工程';
    case 'scenario_simulation':
      return '批量情景模拟';
    default:
      return key;
  }
}

double? _asDouble(Object? value) {
  if (value is double) {
    return value;
  }
  if (value is int) {
    return value.toDouble();
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
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
