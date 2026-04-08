library;

class JobSessionProjection {
  const JobSessionProjection({
    required this.phase,
    this.latestEventType,
    this.latestEventMessage,
    this.latestEventAt,
    this.lastTransitionAt,
    this.currentStepLabel,
    this.eventCount = 0,
    this.stepCount = 0,
    this.artifactCount = 0,
    this.streamRecommended = false,
    this.terminal = false,
  });

  final String phase;
  final String? latestEventType;
  final String? latestEventMessage;
  final DateTime? latestEventAt;
  final DateTime? lastTransitionAt;
  final String? currentStepLabel;
  final int eventCount;
  final int stepCount;
  final int artifactCount;
  final bool streamRecommended;
  final bool terminal;

  factory JobSessionProjection.fromJson(Map<String, dynamic> json) {
    return JobSessionProjection(
      phase: (json['phase'] ?? 'idle').toString(),
      latestEventType: json['latest_event_type']?.toString(),
      latestEventMessage: json['latest_event_message']?.toString(),
      latestEventAt: _parseDateTime(json['latest_event_at']),
      lastTransitionAt: _parseDateTime(json['last_transition_at']),
      currentStepLabel: json['current_step_label']?.toString(),
      eventCount: _asInt(json['event_count']) ?? 0,
      stepCount: _asInt(json['step_count']) ?? 0,
      artifactCount: _asInt(json['artifact_count']) ?? 0,
      streamRecommended: _asBool(json['stream_recommended']) ?? false,
      terminal: _asBool(json['terminal']) ?? false,
    );
  }
}

DateTime? _parseDateTime(Object? value) {
  if (value == null) {
    return null;
  }
  final raw = value.toString();
  if (raw.isEmpty) {
    return null;
  }
  return DateTime.tryParse(raw)?.toLocal();
}

int? _asInt(Object? value) {
  if (value is int) {
    return value;
  }
  return int.tryParse(value?.toString() ?? '');
}

bool? _asBool(Object? value) {
  if (value is bool) {
    return value;
  }
  final raw = value?.toString().trim().toLowerCase();
  if (raw == 'true') {
    return true;
  }
  if (raw == 'false') {
    return false;
  }
  return null;
}
