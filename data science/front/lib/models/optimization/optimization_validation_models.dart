part of '../optimization_result.dart';

/// 数据覆盖信息
class DataCoverage {
  DataCoverage({this.start, this.end, this.spanDays, this.rows});

  final String? start;
  final String? end;
  final int? spanDays;
  final int? rows;

  factory DataCoverage.fromJson(Map<String, dynamic> json) {
    return DataCoverage(
      start: _toNullableString(json['start']),
      end: _toNullableString(json['end']),
      spanDays: _toNullableInt(json['span_days']),
      rows: _toNullableInt(json['rows']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (start != null) 'start': start,
      if (end != null) 'end': end,
      if (spanDays != null) 'span_days': spanDays,
      if (rows != null) 'rows': rows,
    };
  }
}

/// 验证摘要信息
class ValidationSummary {
  ValidationSummary({
    this.method,
    this.cvFolds,
    this.cvMaeMean,
    this.cvMaeStd,
    this.cvScores,
    this.holdoutMae,
    this.holdoutRmse,
    this.holdoutR2,
    this.holdoutMape,
  });

  final String? method;
  final int? cvFolds;
  final double? cvMaeMean;
  final double? cvMaeStd;
  final List<double>? cvScores;
  final double? holdoutMae;
  final double? holdoutRmse;
  final double? holdoutR2;
  final double? holdoutMape;

  factory ValidationSummary.fromJson(Map<String, dynamic> json) {
    return ValidationSummary(
      method: _toNullableString(json['method']),
      cvFolds: _toNullableInt(json['cv_folds']),
      cvMaeMean: _toNullableDouble(json['cv_mae_mean']),
      cvMaeStd: _toNullableDouble(json['cv_mae_std']),
      cvScores: _toDoubleList(json['cv_scores']),
      holdoutMae: _toNullableDouble(json['holdout_mae']),
      holdoutRmse: _toNullableDouble(json['holdout_rmse']),
      holdoutR2: _toNullableDouble(json['holdout_r2']),
      holdoutMape: _toNullableDouble(json['holdout_mape']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (method != null) 'method': method,
      if (cvFolds != null) 'cv_folds': cvFolds,
      if (cvMaeMean != null) 'cv_mae_mean': cvMaeMean,
      if (cvMaeStd != null) 'cv_mae_std': cvMaeStd,
      if (cvScores != null) 'cv_scores': cvScores,
      if (holdoutMae != null) 'holdout_mae': holdoutMae,
      if (holdoutRmse != null) 'holdout_rmse': holdoutRmse,
      if (holdoutR2 != null) 'holdout_r2': holdoutR2,
      if (holdoutMape != null) 'holdout_mape': holdoutMape,
    };
  }
}

/// 自动模型选择信息
class AutoSelection {
  AutoSelection({
    required this.enabled,
    required this.candidatesEvaluated,
    required this.winner,
    required this.improvementOverBaseline,
    this.allScores,
    this.validationMethod,
    this.cvFolds,
    this.cvDetails,
  });

  final bool enabled;
  final List<String> candidatesEvaluated;
  final String winner;
  final String improvementOverBaseline;
  final Map<String, dynamic>? allScores;
  final String? validationMethod;
  final int? cvFolds;
  final Map<String, dynamic>? cvDetails;

  factory AutoSelection.fromJson(Map<String, dynamic> json) {
    return AutoSelection(
      enabled: _toNullableBool(json['enabled']) ?? false,
      candidatesEvaluated: _toStringList(json['candidates_evaluated']) ?? [],
      winner: _toNullableString(json['winner']) ?? 'unknown',
      improvementOverBaseline:
          _toNullableString(json['improvement_over_baseline']) ?? 'N/A',
      allScores: _toStringDynamicMap(json['all_scores']),
      validationMethod: _toNullableString(json['validation_method']),
      cvFolds: _toNullableInt(json['cv_folds']),
      cvDetails: _toStringDynamicMap(json['cv_details']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'enabled': enabled,
      'candidates_evaluated': candidatesEvaluated,
      'winner': winner,
      'improvement_over_baseline': improvementOverBaseline,
      if (allScores != null) 'all_scores': allScores,
      if (validationMethod != null) 'validation_method': validationMethod,
      if (cvFolds != null) 'cv_folds': cvFolds,
      if (cvDetails != null) 'cv_details': cvDetails,
    };
  }

  String get _normalizedValidationMethod =>
      validationMethod?.trim().toLowerCase() ?? '';

  bool get usedTimeSeriesCV {
    return _normalizedValidationMethod == 'timeseriessplit' ||
        _normalizedValidationMethod == 'time_series_split';
  }

  String get validationMethodFormatted {
    if (usedTimeSeriesCV) {
      return '时序交叉验证 (${cvFolds ?? 5}折)';
    }
    if (_normalizedValidationMethod == 'holdout') {
      return '留出法';
    }
    return validationMethod ?? 'N/A';
  }
}

/// 模型指标
class ModelMetrics {
  ModelMetrics({
    this.trainMae,
    this.trainRmse,
    this.testMae,
    this.testRmse,
    this.mape,
    this.r2Score,
    this.sampleCount,
    this.lastDataPoint,
  });

  final double? trainMae;
  final double? trainRmse;
  final double? testMae;
  final double? testRmse;
  final double? mape;
  final double? r2Score;
  final int? sampleCount;
  final String? lastDataPoint;

  factory ModelMetrics.fromJson(Map<String, dynamic> json) {
    return ModelMetrics(
      trainMae: _toNullableDouble(json['train_mae']),
      trainRmse: _toNullableDouble(json['train_rmse']),
      testMae: _toNullableDouble(json['test_mae']),
      testRmse: _toNullableDouble(json['test_rmse']),
      mape: _toNullableDouble(json['mape']),
      r2Score: _toNullableDouble(json['r2_score']),
      sampleCount: _toNullableInt(json['sample_count']),
      lastDataPoint: _toNullableString(json['last_data_point']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (trainMae != null) 'train_mae': trainMae,
      if (trainRmse != null) 'train_rmse': trainRmse,
      if (testMae != null) 'test_mae': testMae,
      if (testRmse != null) 'test_rmse': testRmse,
      if (mape != null) 'mape': mape,
      if (r2Score != null) 'r2_score': r2Score,
      if (sampleCount != null) 'sample_count': sampleCount,
      if (lastDataPoint != null) 'last_data_point': lastDataPoint,
    };
  }

  double? get mae => testMae;
}
