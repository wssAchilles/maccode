part of '../analysis_result.dart';

/// 统计检验结果类
class StatisticalResult {
  final bool success;
  final Map<String, NormalityTest>? normalityTests;
  final List<String>? nonNormalColumns;
  final TestSummary? summary;
  final List<String>? suggestions;
  final String? error;
  final String? message;

  StatisticalResult({
    required this.success,
    this.normalityTests,
    this.nonNormalColumns,
    this.summary,
    this.suggestions,
    this.error,
    this.message,
  });

  factory StatisticalResult.fromJson(Map<String, dynamic> json) {
    try {
      final success = json['success'] ?? false;

      if (!success) {
        return StatisticalResult(
          success: false,
          error: json['error'],
          message: json['message'],
        );
      }

      return StatisticalResult(
        success: true,
        normalityTests: json['normality_tests'] != null
            ? (json['normality_tests'] as Map<String, dynamic>).map(
                (key, value) => MapEntry(key, NormalityTest.fromJson(value)),
              )
            : null,
        nonNormalColumns: json['non_normal_columns'] != null
            ? List<String>.from(json['non_normal_columns'])
            : null,
        summary: json['summary'] != null
            ? TestSummary.fromJson(json['summary'])
            : null,
        suggestions: json['suggestions'] != null
            ? List<String>.from(json['suggestions'])
            : null,
      );
    } catch (e) {
      throw FormatException('Failed to parse StatisticalResult: $e');
    }
  }
}

/// 正态性检验
class NormalityTest {
  final String? testName;
  final double? statistic;
  final double? pValue;
  final bool? isNormal;
  final String? distribution;
  final int? nSamples;
  final double? skewness;
  final double? kurtosis;
  final String? error;

  NormalityTest({
    this.testName,
    this.statistic,
    this.pValue,
    this.isNormal,
    this.distribution,
    this.nSamples,
    this.skewness,
    this.kurtosis,
    this.error,
  });

  factory NormalityTest.fromJson(Map<String, dynamic> json) {
    if (json['error'] != null) {
      return NormalityTest(error: json['error']);
    }

    return NormalityTest(
      testName: json['test_name'],
      statistic: (json['statistic'] as num?)?.toDouble(),
      pValue: (json['p_value'] as num?)?.toDouble(),
      isNormal: json['is_normal'],
      distribution: json['distribution'],
      nSamples: json['n_samples'],
      skewness: (json['skewness'] as num?)?.toDouble(),
      kurtosis: (json['kurtosis'] as num?)?.toDouble(),
    );
  }
}

/// 检验摘要
class TestSummary {
  final int totalNumericColumns;
  final int normalDistributionCount;
  final int nonNormalDistributionCount;

  TestSummary({
    required this.totalNumericColumns,
    required this.normalDistributionCount,
    required this.nonNormalDistributionCount,
  });

  factory TestSummary.fromJson(Map<String, dynamic> json) {
    return TestSummary(
      totalNumericColumns: json['total_numeric_columns'] ?? 0,
      normalDistributionCount: json['normal_distribution_count'] ?? 0,
      nonNormalDistributionCount: json['non_normal_distribution_count'] ?? 0,
    );
  }
}
