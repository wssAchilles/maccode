part of '../analysis_result.dart';

/// 质量分析结果类
class QualityAnalysis {
  final bool success;
  final double? qualityScore;
  final Map<String, MissingInfo>? missingAnalysis;
  final List<String>? highRiskColumns;
  final Map<String, OutlierInfo>? outlierDetection;
  final DuplicateCheck? duplicateCheck;
  final DataSummary? dataSummary;
  final QualityMetrics? qualityMetrics;
  final List<String>? recommendations;
  final String? error;
  final String? message;

  QualityAnalysis({
    required this.success,
    this.qualityScore,
    this.missingAnalysis,
    this.highRiskColumns,
    this.outlierDetection,
    this.duplicateCheck,
    this.dataSummary,
    this.qualityMetrics,
    this.recommendations,
    this.error,
    this.message,
  });

  factory QualityAnalysis.fromJson(Map<String, dynamic> json) {
    try {
      final success = json['success'] ?? false;

      if (!success) {
        return QualityAnalysis(
          success: false,
          error: json['error'],
          message: json['message'],
        );
      }

      return QualityAnalysis(
        success: true,
        qualityScore: (json['quality_score'] as num?)?.toDouble(),
        missingAnalysis: json['missing_analysis'] != null
            ? (json['missing_analysis'] as Map<String, dynamic>).map(
                (key, value) => MapEntry(key, MissingInfo.fromJson(value)),
              )
            : null,
        highRiskColumns: json['high_risk_columns'] != null
            ? List<String>.from(json['high_risk_columns'])
            : null,
        outlierDetection: json['outlier_detection'] != null
            ? (json['outlier_detection'] as Map<String, dynamic>).map(
                (key, value) => MapEntry(key, OutlierInfo.fromJson(value)),
              )
            : null,
        duplicateCheck: json['duplicate_check'] != null
            ? DuplicateCheck.fromJson(json['duplicate_check'])
            : null,
        dataSummary: json['data_summary'] != null
            ? DataSummary.fromJson(json['data_summary'])
            : null,
        qualityMetrics: json['quality_metrics'] != null
            ? QualityMetrics.fromJson(json['quality_metrics'])
            : null,
        recommendations: json['recommendations'] != null
            ? List<String>.from(json['recommendations'])
            : null,
      );
    } catch (e) {
      throw FormatException('Failed to parse QualityAnalysis: $e');
    }
  }
}

/// 缺失信息
class MissingInfo {
  final int count;
  final double percentage;
  final String riskLevel;

  MissingInfo({
    required this.count,
    required this.percentage,
    required this.riskLevel,
  });

  factory MissingInfo.fromJson(Map<String, dynamic> json) {
    return MissingInfo(
      count: json['count'] ?? 0,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0.0,
      riskLevel: json['risk_level'] ?? 'Unknown',
    );
  }
}

/// 异常值信息
class OutlierInfo {
  final int? count;
  final double? percentage;
  final List<int>? indices;
  final Map<String, double>? bounds;
  final String? error;

  OutlierInfo({
    this.count,
    this.percentage,
    this.indices,
    this.bounds,
    this.error,
  });

  factory OutlierInfo.fromJson(Map<String, dynamic> json) {
    if (json['error'] != null) {
      return OutlierInfo(error: json['error']);
    }

    return OutlierInfo(
      count: json['count'],
      percentage: (json['percentage'] as num?)?.toDouble(),
      indices: json['indices'] != null ? List<int>.from(json['indices']) : null,
      bounds: json['bounds'] != null
          ? Map<String, double>.from(
              (json['bounds'] as Map).map(
                (key, value) =>
                    MapEntry(key.toString(), (value as num).toDouble()),
              ),
            )
          : null,
    );
  }
}

/// 重复检查
class DuplicateCheck {
  final int count;
  final double percentage;
  final List<int> indices;

  DuplicateCheck({
    required this.count,
    required this.percentage,
    required this.indices,
  });

  factory DuplicateCheck.fromJson(Map<String, dynamic> json) {
    return DuplicateCheck(
      count: json['count'] ?? 0,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0.0,
      indices: json['indices'] != null ? List<int>.from(json['indices']) : [],
    );
  }
}

/// 数据摘要
class DataSummary {
  final Map<String, dynamic> numericColumns;
  final Map<String, dynamic> categoricalColumns;
  final Map<String, dynamic> datetimeColumns;

  DataSummary({
    required this.numericColumns,
    required this.categoricalColumns,
    required this.datetimeColumns,
  });

  factory DataSummary.fromJson(Map<String, dynamic> json) {
    return DataSummary(
      numericColumns: json['numeric_columns'] ?? {},
      categoricalColumns: json['categorical_columns'] ?? {},
      datetimeColumns: json['datetime_columns'] ?? {},
    );
  }
}

/// 质量指标
class QualityMetrics {
  final int totalCells;
  final int totalMissing;
  final double missingRate;
  final int totalOutliers;
  final int duplicateRows;

  QualityMetrics({
    required this.totalCells,
    required this.totalMissing,
    required this.missingRate,
    required this.totalOutliers,
    required this.duplicateRows,
  });

  factory QualityMetrics.fromJson(Map<String, dynamic> json) {
    return QualityMetrics(
      totalCells: json['total_cells'] ?? 0,
      totalMissing: json['total_missing'] ?? 0,
      missingRate: (json['missing_rate'] as num?)?.toDouble() ?? 0.0,
      totalOutliers: json['total_outliers'] ?? 0,
      duplicateRows: json['duplicate_rows'] ?? 0,
    );
  }
}
