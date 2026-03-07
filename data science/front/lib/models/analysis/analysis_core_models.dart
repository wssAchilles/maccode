part of '../analysis_result.dart';

/// 主分析结果类
class AnalysisResult {
  final BasicInfo basicInfo;
  final List<Map<String, dynamic>> preview;
  final Map<String, dynamic>? descriptiveStatistics;
  final Map<String, dynamic>? missingData;
  final Map<String, dynamic>? typeDistribution;
  final Map<String, dynamic>? correlationMatrix;
  final QualityAnalysis? qualityAnalysis;
  final CorrelationResult? correlations;
  final StatisticalResult? statisticalTests;

  AnalysisResult({
    required this.basicInfo,
    required this.preview,
    this.descriptiveStatistics,
    this.missingData,
    this.typeDistribution,
    this.correlationMatrix,
    this.qualityAnalysis,
    this.correlations,
    this.statisticalTests,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    try {
      return AnalysisResult(
        basicInfo: BasicInfo.fromJson(json['basic_info'] ?? {}),
        preview: List<Map<String, dynamic>>.from(json['preview'] ?? []),
        descriptiveStatistics: json['descriptive_statistics'],
        missingData: json['missing_data'],
        typeDistribution: json['type_distribution'],
        correlationMatrix: json['correlation_matrix'],
        qualityAnalysis: json['quality_analysis'] != null
            ? QualityAnalysis.fromJson(json['quality_analysis'])
            : null,
        correlations: json['correlations'] != null
            ? CorrelationResult.fromJson(json['correlations'])
            : null,
        statisticalTests: json['statistical_tests'] != null
            ? StatisticalResult.fromJson(json['statistical_tests'])
            : null,
      );
    } catch (e) {
      throw FormatException('Failed to parse AnalysisResult: $e');
    }
  }
}

/// 基本信息类
class BasicInfo {
  final int rows;
  final int columns;
  final List<String> columnNames;
  final Map<String, String> columnTypes;

  BasicInfo({
    required this.rows,
    required this.columns,
    required this.columnNames,
    required this.columnTypes,
  });

  factory BasicInfo.fromJson(Map<String, dynamic> json) {
    try {
      return BasicInfo(
        rows: json['rows'] ?? 0,
        columns: json['columns'] ?? 0,
        columnNames: List<String>.from(json['column_names'] ?? []),
        columnTypes: Map<String, String>.from(json['column_types'] ?? {}),
      );
    } catch (e) {
      throw FormatException('Failed to parse BasicInfo: $e');
    }
  }
}
