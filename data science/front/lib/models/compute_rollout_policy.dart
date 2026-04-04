/// Compute rollout governance model.
library;

class ComputeRolloutPolicy {
  const ComputeRolloutPolicy({
    required this.enabled,
    required this.updatedAt,
    required this.updatedBy,
    this.components = const <ComputeRolloutComponentPolicy>[],
  });

  const ComputeRolloutPolicy.empty()
    : enabled = false,
      updatedAt = '',
      updatedBy = '',
      components = const <ComputeRolloutComponentPolicy>[];

  final bool enabled;
  final String updatedAt;
  final String updatedBy;
  final List<ComputeRolloutComponentPolicy> components;

  factory ComputeRolloutPolicy.fromJson(Map<String, dynamic> json) {
    return ComputeRolloutPolicy(
      enabled: _asBool(json['enabled']) ?? false,
      updatedAt: (json['updated_at'] ?? '').toString(),
      updatedBy: (json['updated_by'] ?? '').toString(),
      components: _mapList(
        json['components'],
        ComputeRolloutComponentPolicy.fromJson,
      ),
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
    required this.notes,
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
  final String notes;
  final List<String> allowedBackends;
  final List<String> allowedModes;

  bool get benchmarkReady => lastBenchmarkAt.isNotEmpty;

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
      notes: (json['notes'] ?? '').toString(),
      allowedBackends: _mapPrimitiveList(json['allowed_backends']),
      allowedModes: _mapPrimitiveList(json['allowed_modes']),
    );
  }
}

List<T> _mapList<T>(
  Object? payload,
  T Function(Map<String, dynamic>) parser,
) {
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
