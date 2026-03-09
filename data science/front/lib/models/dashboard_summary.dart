/// 驾驶舱摘要模型
library;

import 'job_record.dart';

class DashboardSummary {
  const DashboardSummary({
    required this.systemStatus,
    required this.kpis,
    required this.recentJobs,
    required this.recentAssets,
    required this.recentHistory,
    required this.alerts,
  });

  final List<SystemStatusItem> systemStatus;
  final DashboardKpis kpis;
  final List<JobRecord> recentJobs;
  final List<DatasetAsset> recentAssets;
  final List<AuditActivity> recentHistory;
  final List<DashboardAlert> alerts;

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      systemStatus: _mapList(
        json['system_status'],
        SystemStatusItem.fromJson,
      ),
      kpis: DashboardKpis.fromJson(
        json['kpis'] is Map
            ? Map<String, dynamic>.from(json['kpis'] as Map)
            : const {},
      ),
      recentJobs: _mapList(json['recent_jobs'], JobRecord.fromJson),
      recentAssets: _mapList(json['recent_assets'], DatasetAsset.fromJson),
      recentHistory: _mapList(json['recent_history'], AuditActivity.fromJson),
      alerts: _mapList(json['alerts'], DashboardAlert.fromJson),
    );
  }
}

class DashboardKpis {
  const DashboardKpis({
    required this.datasetCount,
    required this.analysisCount,
    required this.modelCount,
    required this.jobs24h,
    required this.failedJobs,
  });

  final int datasetCount;
  final int analysisCount;
  final int modelCount;
  final int jobs24h;
  final int failedJobs;

  factory DashboardKpis.fromJson(Map<String, dynamic> json) {
    return DashboardKpis(
      datasetCount: _asInt(json['dataset_count']) ?? 0,
      analysisCount: _asInt(json['analysis_count']) ?? 0,
      modelCount: _asInt(json['model_count']) ?? 0,
      jobs24h: _asInt(json['jobs_24h']) ?? 0,
      failedJobs: _asInt(json['failed_jobs']) ?? 0,
    );
  }
}

class SystemStatusItem {
  const SystemStatusItem({
    required this.key,
    required this.label,
    required this.status,
    required this.message,
  });

  final String key;
  final String label;
  final String status;
  final String message;

  factory SystemStatusItem.fromJson(Map<String, dynamic> json) {
    return SystemStatusItem(
      key: (json['key'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
      status: (json['status'] ?? 'unknown').toString(),
      message: (json['message'] ?? '').toString(),
    );
  }
}

class DatasetAsset {
  const DatasetAsset({
    required this.id,
    required this.filename,
    this.qualityScore,
    this.createdAt,
  });

  final String id;
  final String filename;
  final double? qualityScore;
  final DateTime? createdAt;

  factory DatasetAsset.fromJson(Map<String, dynamic> json) {
    return DatasetAsset(
      id: (json['id'] ?? '').toString(),
      filename: (json['filename'] ?? 'Unknown').toString(),
      qualityScore: _asDouble(json['quality_score']),
      createdAt: _parseDateTime(json['created_at']),
    );
  }
}

class DashboardAlert {
  const DashboardAlert({
    required this.severity,
    required this.title,
    required this.message,
  });

  final String severity;
  final String title;
  final String message;

  factory DashboardAlert.fromJson(Map<String, dynamic> json) {
    return DashboardAlert(
      severity: (json['severity'] ?? 'info').toString(),
      title: (json['title'] ?? '系统提醒').toString(),
      message: (json['message'] ?? '').toString(),
    );
  }
}

List<T> _mapList<T>(Object? source, T Function(Map<String, dynamic>) parser) {
  if (source is! List) {
    return <T>[];
  }

  return source.whereType<Object?>().map((item) {
    if (item is Map<String, dynamic>) {
      return parser(item);
    }
    if (item is Map) {
      return parser(Map<String, dynamic>.from(item));
    }
    return null;
  }).whereType<T>().toList(growable: false);
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
