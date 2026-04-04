/// Helpers for operation-level compute telemetry rendering.
library;

class OperationComputeMetric {
  const OperationComputeMetric({
    required this.key,
    required this.label,
    required this.backend,
    required this.rolloutMode,
    required this.durationMs,
    required this.rows,
    required this.context,
    required this.nativeEnabled,
    required this.nativeAvailable,
  });

  final String key;
  final String label;
  final String backend;
  final String rolloutMode;
  final double durationMs;
  final int rows;
  final String context;
  final bool nativeEnabled;
  final bool nativeAvailable;
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
      durationMs: _asDouble(payload['duration_ms']) ?? 0,
      rows: _asInt(payload['rows']) ?? 0,
      context: (payload['context'] ?? '').toString(),
      nativeEnabled: _asBool(payload['native_enabled']) ?? false,
      nativeAvailable: _asBool(payload['native_available']) ?? false,
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
  return '${lead.label} · ${lead.durationMs.toStringAsFixed(1)}ms · ${lead.backend}$rollout$context$suffix';
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
