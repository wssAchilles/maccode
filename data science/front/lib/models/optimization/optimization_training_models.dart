part of '../optimization_result.dart';

/// 训练配置信息
class TrainingConfig {
  TrainingConfig({
    this.testSize,
    this.randomState,
    this.useTimeSeriesCV,
    this.cvFolds,
    this.useLogTransform,
    this.removeOutliers,
    this.tuneHyperparameters,
  });

  final double? testSize;
  final int? randomState;
  final bool? useTimeSeriesCV;
  final int? cvFolds;
  final bool? useLogTransform;
  final bool? removeOutliers;
  final bool? tuneHyperparameters;

  factory TrainingConfig.fromJson(Map<String, dynamic> json) {
    return TrainingConfig(
      testSize: _toNullableDouble(json['test_size']),
      randomState: _toNullableInt(json['random_state']),
      useTimeSeriesCV:
          _toNullableBool(json['use_time_series_cv']) ??
          _toNullableBool(json['time_series_split']),
      cvFolds: _toNullableInt(json['cv_folds']),
      useLogTransform: _toNullableBool(json['use_log_transform']),
      removeOutliers: _toNullableBool(json['remove_outliers']),
      tuneHyperparameters:
          _toNullableBool(json['hyperparameter_tuning']) ??
          _toNullableBool(json['tune_hyperparameters']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      if (testSize != null) 'test_size': testSize,
      if (randomState != null) 'random_state': randomState,
      if (useTimeSeriesCV != null) 'use_time_series_cv': useTimeSeriesCV,
      if (cvFolds != null) 'cv_folds': cvFolds,
      if (useLogTransform != null) 'use_log_transform': useLogTransform,
      if (removeOutliers != null) 'remove_outliers': removeOutliers,
      if (tuneHyperparameters != null)
        'hyperparameter_tuning': tuneHyperparameters,
    };
  }
}
