part of '../analysis_result.dart';

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
        pearson: CorrelationCoefficient(
          correlation: 0,
          pValue: 1,
          significant: false,
        ),
        spearman: CorrelationCoefficient(
          correlation: 0,
          pValue: 1,
          significant: false,
        ),
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
