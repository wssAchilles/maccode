part of '../optimization_result.dart';

/// ML模型信息
class ModelInfo {
  ModelInfo({
    required this.modelType,
    required this.status,
    this.message,
    this.modelVersion,
    this.trainedAt,
    this.validationSummary,
    this.dataCoverage,
    this.dataSource,
    this.metrics,
    this.trainingSamples,
    this.autoSelection,
    this.hyperparameters,
    this.featureCount,
    this.featureColumns,
    this.trainingConfig,
  });

  final String modelType;
  final String? modelVersion;
  final String? trainedAt;
  final ModelMetrics? metrics;
  final ValidationSummary? validationSummary;
  final DataCoverage? dataCoverage;
  final int? trainingSamples;
  final String? dataSource;
  final String? status;
  final String? message;
  final AutoSelection? autoSelection;
  final Map<String, dynamic>? hyperparameters;
  final int? featureCount;
  final List<String>? featureColumns;
  final TrainingConfig? trainingConfig;

  factory ModelInfo.fromJson(Map<String, dynamic> json) {
    try {
      return ModelInfo(
        modelType: _toNullableString(json['model_type']) ?? 'Unknown',
        modelVersion: _toNullableString(json['model_version']),
        trainedAt: _toNullableString(json['trained_at']),
        validationSummary:
            _toStringDynamicMap(json['validation_summary']) != null
            ? ValidationSummary.fromJson(
                _toStringDynamicMap(json['validation_summary'])!,
              )
            : null,
        dataCoverage: _toStringDynamicMap(json['data_coverage']) != null
            ? DataCoverage.fromJson(_toStringDynamicMap(json['data_coverage'])!)
            : null,
        dataSource: _toNullableString(json['data_source']),
        status: _toNullableString(json['status']) ?? 'unknown',
        message: _toNullableString(json['message']),
        trainingSamples: _toNullableInt(json['training_samples']),
        metrics: _toStringDynamicMap(json['metrics']) != null
            ? ModelMetrics.fromJson(_toStringDynamicMap(json['metrics'])!)
            : null,
        autoSelection: _toStringDynamicMap(json['auto_selection']) != null
            ? AutoSelection.fromJson(
                _toStringDynamicMap(json['auto_selection'])!,
              )
            : null,
        hyperparameters: _toStringDynamicMap(json['hyperparameters']),
        featureCount: _toNullableInt(json['feature_count']),
        featureColumns: _toStringList(json['feature_columns']),
        trainingConfig: _toStringDynamicMap(json['training_config']) != null
            ? TrainingConfig.fromJson(
                _toStringDynamicMap(json['training_config'])!,
              )
            : null,
      );
    } catch (e) {
      throw FormatException('Failed to parse ModelInfo: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'model_type': modelType,
      if (modelVersion != null) 'model_version': modelVersion,
      if (trainedAt != null) 'trained_at': trainedAt,
      if (validationSummary != null)
        'validation_summary': validationSummary!.toJson(),
      if (dataCoverage != null) 'data_coverage': dataCoverage!.toJson(),
      if (metrics != null) 'metrics': metrics?.toJson(),
      if (trainingSamples != null) 'training_samples': trainingSamples,
      if (dataSource != null) 'data_source': dataSource,
      'status': status,
      if (message != null) 'message': message,
      if (autoSelection != null) 'auto_selection': autoSelection!.toJson(),
      if (hyperparameters != null) 'hyperparameters': hyperparameters,
      if (featureCount != null) 'feature_count': featureCount,
      if (featureColumns != null) 'feature_columns': featureColumns,
      if (trainingConfig != null) 'training_config': trainingConfig!.toJson(),
    };
  }

  String get trainedAtFormatted {
    if (trainedAt == null) return 'N/A';
    try {
      final date = DateTime.parse(trainedAt!);
      return '${date.month}月${date.day}日 '
          '${date.hour}:${date.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return trainedAt!;
    }
  }

  String get maeFormatted {
    if (metrics == null || metrics?.mae == null) return 'N/A';
    return '${metrics!.mae!.toStringAsFixed(2)} kW';
  }

  bool get usedAutoSelection => autoSelection?.enabled ?? false;
  String get winnerModel => autoSelection?.winner ?? modelType;
  String get improvementOverBaseline =>
      autoSelection?.improvementOverBaseline ?? 'N/A';
  String get validationMethodFormatted =>
      autoSelection?.validationMethodFormatted ?? 'N/A';
  bool get usedTimeSeriesCV => autoSelection?.usedTimeSeriesCV ?? false;
  bool get isValid => status == 'active';
}
