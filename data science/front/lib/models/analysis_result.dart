/// 数据分析结果模型
/// 对应后端返回的增强分析结构
library;

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
                (key, value) => MapEntry(key.toString(), (value as num).toDouble()),
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

/// 相关性分析结果类
class CorrelationResult {
  final bool success;
  final List<CorrelationPair>? correlations;
  final List<HighCorrelation>? highCorrelations;
  final Map<String, dynamic>? pearsonMatrix;
  final Map<String, dynamic>? spearmanMatrix;
  final List<String>? suggestions;
  final List<String>? numericColumns;
  final String? error;
  final String? message;

  CorrelationResult({
    required this.success,
    this.correlations,
    this.highCorrelations,
    this.pearsonMatrix,
    this.spearmanMatrix,
    this.suggestions,
    this.numericColumns,
    this.error,
    this.message,
  });

  factory CorrelationResult.fromJson(Map<String, dynamic> json) {
    try {
      final success = json['success'] ?? false;

      if (!success) {
        return CorrelationResult(
          success: false,
          error: json['error'],
          message: json['message'],
        );
      }

      return CorrelationResult(
        success: true,
        correlations: json['correlations'] != null
            ? (json['correlations'] as List)
                .map((e) => CorrelationPair.fromJson(e))
                .toList()
            : null,
        highCorrelations: json['high_correlations'] != null
            ? (json['high_correlations'] as List)
                .map((e) => HighCorrelation.fromJson(e))
                .toList()
            : null,
        pearsonMatrix: json['pearson_matrix'],
        spearmanMatrix: json['spearman_matrix'],
        suggestions: json['suggestions'] != null
            ? List<String>.from(json['suggestions'])
            : null,
        numericColumns: json['numeric_columns'] != null
            ? List<String>.from(json['numeric_columns'])
            : null,
      );
    } catch (e) {
      throw FormatException('Failed to parse CorrelationResult: $e');
    }
  }
}

/// 相关性对
class CorrelationPair {
  final String variableX;
  final String variableY;
  final CorrelationCoefficient pearson;
  final CorrelationCoefficient spearman;
  final int nSamples;
  final String? error;

  CorrelationPair({
    required this.variableX,
    required this.variableY,
    required this.pearson,
    required this.spearman,
    required this.nSamples,
    this.error,
  });

  factory CorrelationPair.fromJson(Map<String, dynamic> json) {
    if (json['error'] != null) {
      return CorrelationPair(
        variableX: json['variable_x'] ?? '',
        variableY: json['variable_y'] ?? '',
        pearson: CorrelationCoefficient(correlation: 0, pValue: 1, significant: false),
        spearman: CorrelationCoefficient(correlation: 0, pValue: 1, significant: false),
        nSamples: 0,
        error: json['error'],
      );
    }

    return CorrelationPair(
      variableX: json['variable_x'] ?? '',
      variableY: json['variable_y'] ?? '',
      pearson: CorrelationCoefficient.fromJson(json['pearson']),
      spearman: CorrelationCoefficient.fromJson(json['spearman']),
      nSamples: json['n_samples'] ?? 0,
    );
  }
}

/// 相关系数
class CorrelationCoefficient {
  final double correlation;
  final double pValue;
  final bool significant;

  CorrelationCoefficient({
    required this.correlation,
    required this.pValue,
    required this.significant,
  });

  factory CorrelationCoefficient.fromJson(Map<String, dynamic> json) {
    return CorrelationCoefficient(
      correlation: (json['correlation'] as num?)?.toDouble() ?? 0.0,
      pValue: (json['p_value'] as num?)?.toDouble() ?? 1.0,
      significant: json['significant'] ?? false,
    );
  }
}

/// 高相关性
class HighCorrelation {
  final List<String> variables;
  final double correlation;
  final String type;

  HighCorrelation({
    required this.variables,
    required this.correlation,
    required this.type,
  });

  factory HighCorrelation.fromJson(Map<String, dynamic> json) {
    return HighCorrelation(
      variables: List<String>.from(json['variables'] ?? []),
      correlation: (json['correlation'] as num?)?.toDouble() ?? 0.0,
      type: json['type'] ?? 'unknown',
    );
  }
}

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
