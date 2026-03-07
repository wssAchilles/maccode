/// 历史记录模型
library;

class HistoryRecord {
  const HistoryRecord({
    required this.id,
    required this.filename,
    this.qualityScore,
    this.createdAt,
    required this.raw,
  });

  final String id;
  final String filename;
  final double? qualityScore;
  final DateTime? createdAt;
  final Map<String, dynamic> raw;

  bool get hasValidId => id.isNotEmpty;
  Map<String, dynamic>? get summary => _asMap(raw['summary']);
  Map<String, dynamic>? get qualityAnalysis =>
      _asMap(summary?['quality_analysis']);
  Map<String, dynamic>? get correlations =>
      _asMap(summary?['correlations'] ?? summary?['correlation_analysis']);
  Map<String, dynamic>? get statisticalTests =>
      _asMap(summary?['statistical_tests']);
  Map<String, dynamic>? get basicInfo => _asMap(summary?['basic_info']);
  dynamic get preview => summary?['preview'] ?? raw['preview'];

  factory HistoryRecord.fromJson(Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);

    return HistoryRecord(
      id: (normalized['id'] ?? '').toString(),
      filename: (normalized['filename'] ?? 'Unknown').toString(),
      qualityScore:
          _parseQualityScore(normalized['quality_score']) ??
          _parseNestedQualityScore(normalized['summary']),
      createdAt: _parseCreatedAt(normalized['created_at']),
      raw: normalized,
    );
  }

  Map<String, dynamic> toJson() {
    final json = Map<String, dynamic>.from(raw);
    json['id'] = id;
    json['filename'] = filename;

    if (qualityScore != null) {
      json['quality_score'] = qualityScore;
    }

    if (createdAt != null) {
      json['created_at'] = createdAt!.toIso8601String();
    }

    return json;
  }

  static double? _parseQualityScore(dynamic value) {
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  static double? _parseNestedQualityScore(dynamic value) {
    final summary = _asMap(value);
    final qualityAnalysis = _asMap(summary?['quality_analysis']);
    return _parseQualityScore(qualityAnalysis?['quality_score']);
  }

  static DateTime? _parseCreatedAt(dynamic value) {
    if (value == null) return null;

    if (value is DateTime) {
      return value;
    }

    if (value is String) {
      return DateTime.tryParse(value);
    }

    if (value is int) {
      return DateTime.fromMillisecondsSinceEpoch(value);
    }

    if (value is Map) {
      final seconds = value['_seconds'];
      if (seconds is int) {
        return DateTime.fromMillisecondsSinceEpoch(seconds * 1000);
      }
    }

    return null;
  }

  static Map<String, dynamic>? _asMap(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }

    if (value is Map) {
      return value.map((key, mapValue) => MapEntry(key.toString(), mapValue));
    }

    return null;
  }
}
