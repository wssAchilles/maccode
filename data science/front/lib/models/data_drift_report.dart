/// 数据漂移检测结果模型
library;

class DataDriftReport {
  const DataDriftReport({
    required this.overallStatus,
    required this.recommendation,
    required this.report,
    required this.summary,
    required this.features,
    required this.featureCount,
  });

  final String overallStatus;
  final String recommendation;
  final String report;
  final DriftSummary summary;
  final List<FeatureDriftStat> features;
  final int featureCount;

  List<FeatureDriftStat> get driftedFeatures =>
      features.where((item) => item.status == 'drift').toList(growable: false);

  List<FeatureDriftStat> get warningFeatures => features
      .where((item) => item.status == 'warning')
      .toList(growable: false);

  factory DataDriftReport.fromJson(Map<String, dynamic> json) {
    final payload = json['drift_results'] is Map
        ? Map<String, dynamic>.from(json['drift_results'] as Map)
        : json;
    final rawFeatures = payload['features'];
    final featureStats = <FeatureDriftStat>[];

    if (rawFeatures is Map) {
      for (final entry in rawFeatures.entries) {
        final value = entry.value;
        if (value is Map<String, dynamic>) {
          featureStats.add(
            FeatureDriftStat.fromJson(entry.key.toString(), value),
          );
        } else if (value is Map) {
          featureStats.add(
            FeatureDriftStat.fromJson(
              entry.key.toString(),
              Map<String, dynamic>.from(value),
            ),
          );
        }
      }
    }

    featureStats.sort((a, b) => b.psi.compareTo(a.psi));

    return DataDriftReport(
      overallStatus: (payload['overall_status'] ?? 'unknown').toString(),
      recommendation: (payload['recommendation'] ?? '暂无建议').toString(),
      report: (json['report'] ?? payload['report'] ?? '').toString(),
      summary: DriftSummary.fromJson(
        payload['summary'] is Map
            ? Map<String, dynamic>.from(payload['summary'] as Map)
            : const <String, dynamic>{},
      ),
      features: featureStats,
      featureCount: _asInt(payload['n_features']) ?? featureStats.length,
    );
  }
}

class DriftSummary {
  const DriftSummary({
    required this.stable,
    required this.warning,
    required this.drift,
  });

  final int stable;
  final int warning;
  final int drift;

  factory DriftSummary.fromJson(Map<String, dynamic> json) {
    return DriftSummary(
      stable: _asInt(json['stable']) ?? 0,
      warning: _asInt(json['warning']) ?? 0,
      drift: _asInt(json['drift']) ?? 0,
    );
  }
}

class FeatureDriftStat {
  const FeatureDriftStat({
    required this.name,
    required this.psi,
    required this.status,
    required this.meanShift,
    this.stdRatio,
  });

  final String name;
  final double psi;
  final String status;
  final double meanShift;
  final double? stdRatio;

  factory FeatureDriftStat.fromJson(String name, Map<String, dynamic> json) {
    return FeatureDriftStat(
      name: name,
      psi: _asDouble(json['psi']) ?? 0,
      status: (json['status'] ?? 'unknown').toString(),
      meanShift: _asDouble(json['mean_shift']) ?? 0,
      stdRatio: _asDouble(json['std_ratio']),
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
