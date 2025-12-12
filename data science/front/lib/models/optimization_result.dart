/// 能源优化结果模型
/// 对应后端 /api/optimization/run 返回的数据结构
library;

/// 优化响应顶层模型
class OptimizationResponse {
  final bool success;
  final OptimizationData? optimization;
  final PredictionInfo? prediction;
  final BatteryConfig? batteryConfig;
  final ModelInfo? modelInfo;
  final ModelExplainability? modelExplainability;
  final String? error;
  final String? message;

  OptimizationResponse({
    required this.success,
    this.optimization,
    this.prediction,
    this.batteryConfig,
    this.modelInfo,
    this.modelExplainability,
    this.error,
    this.message,
  });

  factory OptimizationResponse.fromJson(Map<String, dynamic> json) {
    try {
      return OptimizationResponse(
        success: json['success'] as bool? ?? false,
        optimization: json['optimization'] != null
            ? OptimizationData.fromJson(json['optimization'] as Map<String, dynamic>)
            : null,
        prediction: json['prediction'] != null
            ? PredictionInfo.fromJson(json['prediction'] as Map<String, dynamic>)
            : null,
        batteryConfig: json['battery_config'] != null
            ? BatteryConfig.fromJson(json['battery_config'] as Map<String, dynamic>)
            : null,
        modelInfo: json['model_info'] != null
            ? ModelInfo.fromJson(json['model_info'] as Map<String, dynamic>)
            : null,
        modelExplainability: json['model_explainability'] != null
            ? ModelExplainability.fromJson(json['model_explainability'] as Map<String, dynamic>)
            : null,
        error: json['error'] as String?,
        message: json['message'] as String?,
      );
    } catch (e) {
      throw FormatException('Failed to parse OptimizationResponse: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'success': success,
      if (optimization != null) 'optimization': optimization!.toJson(),
      if (prediction != null) 'prediction': prediction!.toJson(),
      if (batteryConfig != null) 'battery_config': batteryConfig!.toJson(),
      if (modelInfo != null) 'model_info': modelInfo!.toJson(),
      if (modelExplainability != null) 'model_explainability': modelExplainability!.toJson(),
      if (error != null) 'error': error,
      if (message != null) 'message': message,
    };
  }

  bool get isSuccess => success && error == null;
  bool get isFailure => !success || error != null;
}

/// 优化数据主体
class OptimizationData {
  final String status;
  final List<ChartDataPoint> chartData;
  final OptimizationSummary summary;
  final OptimizationStrategy strategy;

  OptimizationData({
    required this.status,
    required this.chartData,
    required this.summary,
    required this.strategy,
  });

  factory OptimizationData.fromJson(Map<String, dynamic> json) {
    try {
      return OptimizationData(
        status: json['status'] as String? ?? 'Unknown',
        chartData: (json['chart_data'] as List<dynamic>?)
                ?.map((item) => ChartDataPoint.fromJson(item as Map<String, dynamic>))
                .toList() ??
            [],
        summary: OptimizationSummary.fromJson(json['summary'] as Map<String, dynamic>? ?? {}),
        strategy: OptimizationStrategy.fromJson(json['strategy'] as Map<String, dynamic>? ?? {}),
      );
    } catch (e) {
      throw FormatException('Failed to parse OptimizationData: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'chart_data': chartData.map((e) => e.toJson()).toList(),
      'summary': summary.toJson(),
      'strategy': strategy.toJson(),
    };
  }

  bool get isOptimal => status == 'Optimal';
  int get hoursCount => chartData.length;
}

/// 图表数据点 - 每小时的详细数据
class ChartDataPoint {
  final int hour;
  final String datetime;
  final double load;
  final double price;
  final double batteryAction; // 正数为充电，负数为放电
  final double chargePower;
  final double dischargePower;
  final double soc; // State of Charge (0-100%)
  final double storedEnergy;
  final double gridPower;

  ChartDataPoint({
    required this.hour,
    required this.datetime,
    required this.load,
    required this.price,
    required this.batteryAction,
    required this.chargePower,
    required this.dischargePower,
    required this.soc,
    required this.storedEnergy,
    required this.gridPower,
  });

  factory ChartDataPoint.fromJson(Map<String, dynamic> json) {
    try {
      return ChartDataPoint(
        hour: json['hour'] as int? ?? 0,
        datetime: json['datetime'] as String? ?? '',
        load: _toDouble(json['load']),
        price: _toDouble(json['price']),
        batteryAction: _toDouble(json['battery_action']),
        chargePower: _toDouble(json['charge_power']),
        dischargePower: _toDouble(json['discharge_power']),
        soc: _toDouble(json['soc']),
        storedEnergy: _toDouble(json['stored_energy']),
        gridPower: _toDouble(json['grid_power']),
      );
    } catch (e) {
      throw FormatException('Failed to parse ChartDataPoint: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'hour': hour,
      'datetime': datetime,
      'load': load,
      'price': price,
      'battery_action': batteryAction,
      'charge_power': chargePower,
      'discharge_power': dischargePower,
      'soc': soc,
      'stored_energy': storedEnergy,
      'grid_power': gridPower,
    };
  }

  /// 是否在充电
  bool get isCharging => batteryAction > 0.01;

  /// 是否在放电
  bool get isDischarging => batteryAction < -0.01;

  /// 是否待机
  bool get isIdle => !isCharging && !isDischarging;

  /// 电池状态描述
  String get batteryStatus {
    if (isCharging) return '充电';
    if (isDischarging) return '放电';
    return '待机';
  }

  /// 价格时段
  String get priceLabel {
    if (price <= 0.3) return '谷时';
    if (price <= 0.6) return '平时';
    return '峰时';
  }

  /// 辅助方法: 安全转换为 double
  static double _toDouble(dynamic value) {
    if (value == null) return 0.0;
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0.0;
    return 0.0;
  }
}

/// 优化摘要 - 成本和节省信息
class OptimizationSummary {
  final double totalCostWithoutBattery;
  final double totalCostWithBattery;
  final double savings;
  final double savingsPercent;
  final double totalLoad;
  final double totalCharged;
  final double totalDischarged;
  final double peakLoad;
  final double minLoad;
  final double avgLoad;

  OptimizationSummary({
    required this.totalCostWithoutBattery,
    required this.totalCostWithBattery,
    required this.savings,
    required this.savingsPercent,
    required this.totalLoad,
    required this.totalCharged,
    required this.totalDischarged,
    required this.peakLoad,
    required this.minLoad,
    required this.avgLoad,
  });

  factory OptimizationSummary.fromJson(Map<String, dynamic> json) {
    try {
      return OptimizationSummary(
        totalCostWithoutBattery: ChartDataPoint._toDouble(json['total_cost_without_battery']),
        totalCostWithBattery: ChartDataPoint._toDouble(json['total_cost_with_battery']),
        savings: ChartDataPoint._toDouble(json['savings']),
        savingsPercent: ChartDataPoint._toDouble(json['savings_percent']),
        totalLoad: ChartDataPoint._toDouble(json['total_load']),
        totalCharged: ChartDataPoint._toDouble(json['total_charged']),
        totalDischarged: ChartDataPoint._toDouble(json['total_discharged']),
        peakLoad: ChartDataPoint._toDouble(json['peak_load']),
        minLoad: ChartDataPoint._toDouble(json['min_load']),
        avgLoad: ChartDataPoint._toDouble(json['avg_load']),
      );
    } catch (e) {
      throw FormatException('Failed to parse OptimizationSummary: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'total_cost_without_battery': totalCostWithoutBattery,
      'total_cost_with_battery': totalCostWithBattery,
      'savings': savings,
      'savings_percent': savingsPercent,
      'total_load': totalLoad,
      'total_charged': totalCharged,
      'total_discharged': totalDischarged,
      'peak_load': peakLoad,
      'min_load': minLoad,
      'avg_load': avgLoad,
    };
  }

  /// 循环效率 (放电/充电)
  double get cycleEfficiency {
    if (totalCharged == 0) return 0.0;
    return (totalDischarged / totalCharged) * 100;
  }

  /// 格式化节省金额
  String get savingsFormatted => '${savings.toStringAsFixed(2)} 元';

  /// 格式化节省比例
  String get savingsPercentFormatted => '${savingsPercent.toStringAsFixed(1)}%';
}

/// 优化策略 - 充放电时段
class OptimizationStrategy {
  final List<int> chargingHours;
  final List<int> dischargingHours;
  final int chargingCount;
  final int dischargingCount;

  OptimizationStrategy({
    required this.chargingHours,
    required this.dischargingHours,
    required this.chargingCount,
    required this.dischargingCount,
  });

  factory OptimizationStrategy.fromJson(Map<String, dynamic> json) {
    try {
      return OptimizationStrategy(
        chargingHours: (json['charging_hours'] as List<dynamic>?)
                ?.map((e) => e as int)
                .toList() ??
            [],
        dischargingHours: (json['discharging_hours'] as List<dynamic>?)
                ?.map((e) => e as int)
                .toList() ??
            [],
        chargingCount: json['charging_count'] as int? ?? 0,
        dischargingCount: json['discharging_count'] as int? ?? 0,
      );
    } catch (e) {
      throw FormatException('Failed to parse OptimizationStrategy: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'charging_hours': chargingHours,
      'discharging_hours': dischargingHours,
      'charging_count': chargingCount,
      'discharging_count': dischargingCount,
    };
  }

  /// 格式化充电时段
  String get chargingHoursFormatted {
    if (chargingHours.isEmpty) return '无';
    return chargingHours.map((h) => '${h.toString().padLeft(2, '0')}:00').join(', ');
  }

  /// 格式化放电时段
  String get dischargingHoursFormatted {
    if (dischargingHours.isEmpty) return '无';
    return dischargingHours.map((h) => '${h.toString().padLeft(2, '0')}:00').join(', ');
  }
}

/// 预测信息
class PredictionInfo {
  final String targetDate;
  final double avgLoad;
  final double peakLoad;
  final double minLoad;

  PredictionInfo({
    required this.targetDate,
    required this.avgLoad,
    required this.peakLoad,
    required this.minLoad,
  });

  factory PredictionInfo.fromJson(Map<String, dynamic> json) {
    try {
      return PredictionInfo(
        targetDate: json['target_date'] as String? ?? '',
        avgLoad: ChartDataPoint._toDouble(json['avg_load']),
        peakLoad: ChartDataPoint._toDouble(json['peak_load']),
        minLoad: ChartDataPoint._toDouble(json['min_load']),
      );
    } catch (e) {
      throw FormatException('Failed to parse PredictionInfo: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'target_date': targetDate,
      'avg_load': avgLoad,
      'peak_load': peakLoad,
      'min_load': minLoad,
    };
  }
}

/// 电池配置信息
class BatteryConfig {
  final double capacity;
  final double maxPower;
  final double efficiency;
  final double initialSoc;

  BatteryConfig({
    required this.capacity,
    required this.maxPower,
    required this.efficiency,
    required this.initialSoc,
  });

  factory BatteryConfig.fromJson(Map<String, dynamic> json) {
    try {
      return BatteryConfig(
        capacity: ChartDataPoint._toDouble(json['capacity']),
        maxPower: ChartDataPoint._toDouble(json['max_power']),
        efficiency: ChartDataPoint._toDouble(json['efficiency']),
        initialSoc: ChartDataPoint._toDouble(json['initial_soc']),
      );
    } catch (e) {
      throw FormatException('Failed to parse BatteryConfig: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'capacity': capacity,
      'max_power': maxPower,
      'efficiency': efficiency,
      'initial_soc': initialSoc,
    };
  }

  /// 格式化容量
  String get capacityFormatted => '${capacity.toStringAsFixed(1)} kWh';

  /// 格式化功率
  String get powerFormatted => '${maxPower.toStringAsFixed(1)} kW';

  /// 格式化效率
  String get efficiencyFormatted => '${(efficiency * 100).toStringAsFixed(0)}%';
}

/// ML模型信息
class ModelInfo {
  final String modelType;
  final String? modelVersion;
  final String? trainedAt;
  final ModelMetrics? metrics;
  final int? trainingSamples;
  final String? dataSource;
  final String? status;
  final String? message;
  final AutoSelection? autoSelection;
  final Map<String, dynamic>? hyperparameters;
  final int? featureCount;  // 新增: 使用的特征数量
  final List<String>? featureColumns;  // 新增: 特征列表

  ModelInfo({
    required this.modelType,
    required this.status,
    this.message,
    this.modelVersion,
    this.trainedAt,
    this.dataSource,
    this.metrics,
    this.trainingSamples,
    this.autoSelection,
    this.hyperparameters,
    this.featureCount,
    this.featureColumns,
  });

  factory ModelInfo.fromJson(Map<String, dynamic> json) {
    try {
      return ModelInfo(
        modelType: json['model_type'] as String? ?? 'Unknown',
        modelVersion: json['model_version'] as String?,
        trainedAt: json['trained_at'] as String?,
        dataSource: json['data_source'] as String?,
        status: json['status'] as String? ?? 'unknown',
        message: json['message'] as String?,
        trainingSamples: json['training_samples'] as int?,
        metrics: json['metrics'] != null ? ModelMetrics.fromJson(json['metrics']) : null,
        autoSelection: json['auto_selection'] != null 
            ? AutoSelection.fromJson(json['auto_selection'] as Map<String, dynamic>)
            : null,
        hyperparameters: json['hyperparameters'] as Map<String, dynamic>?,
        featureCount: json['feature_count'] as int?,
        featureColumns: (json['feature_columns'] as List<dynamic>?)
            ?.map((e) => e.toString())
            .toList(),
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
      if (metrics != null) 'metrics': metrics?.toJson(),
      if (trainingSamples != null) 'training_samples': trainingSamples,
      if (dataSource != null) 'data_source': dataSource,
      'status': status,
      if (message != null) 'message': message,
      if (autoSelection != null) 'auto_selection': autoSelection!.toJson(),
      if (hyperparameters != null) 'hyperparameters': hyperparameters,
      if (featureCount != null) 'feature_count': featureCount,
      if (featureColumns != null) 'feature_columns': featureColumns,
    };
  }

  /// 格式化训练时间
  String get trainedAtFormatted {
    if (trainedAt == null) return 'N/A';
    try {
      final date = DateTime.parse(trainedAt!);
      return '${date.month}月${date.day}日 ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      return trainedAt!;
    }
  }

  /// 格式化MAE
  String get maeFormatted {
    if (metrics == null || metrics?.mae == null) return 'N/A';
    return '${metrics!.mae!.toStringAsFixed(2)} kW';
  }

  /// 是否使用了自动模型选择
  bool get usedAutoSelection => autoSelection?.enabled ?? false;
  
  /// 获取自动选择的胜出模型
  String get winnerModel => autoSelection?.winner ?? modelType;
  
  /// 获取相对基准的提升
  String get improvementOverBaseline => autoSelection?.improvementOverBaseline ?? 'N/A';
  
  /// 获取验证方法名称
  String get validationMethodFormatted => autoSelection?.validationMethodFormatted ?? 'N/A';
  
  /// 是否使用了时间序列交叉验证
  bool get usedTimeSeriesCV => autoSelection?.usedTimeSeriesCV ?? false;

  bool get isValid => status == 'active';
}

/// 自动模型选择信息
class AutoSelection {
  final bool enabled;
  final List<String> candidatesEvaluated;
  final String winner;
  final String improvementOverBaseline;
  final Map<String, dynamic>? allScores;
  final String? validationMethod;  // 新增: TimeSeriesSplit 或 HoldOut
  final int? cvFolds;              // 新增: 交叉验证折数
  final Map<String, dynamic>? cvDetails;  // 新增: 交叉验证详细信息

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

  factory AutoSelection.fromJson(Map<String, dynamic> json) {
    return AutoSelection(
      enabled: json['enabled'] as bool? ?? false,
      candidatesEvaluated: (json['candidates_evaluated'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList() ?? [],
      winner: json['winner'] as String? ?? 'unknown',
      improvementOverBaseline: json['improvement_over_baseline'] as String? ?? 'N/A',
      allScores: json['all_scores'] as Map<String, dynamic>?,
      validationMethod: json['validation_method'] as String?,
      cvFolds: json['cv_folds'] as int?,
      cvDetails: json['cv_details'] as Map<String, dynamic>?,
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

  /// 是否使用了时间序列交叉验证
  bool get usedTimeSeriesCV => validationMethod == 'TimeSeriesSplit';
  
  /// 格式化验证方法名称
  String get validationMethodFormatted {
    if (validationMethod == 'TimeSeriesSplit') {
      return '时序交叉验证 (${cvFolds ?? 5}折)';
    } else if (validationMethod == 'HoldOut') {
      return '留出法';
    }
    return validationMethod ?? 'N/A';
  }
}

/// 模型指标
class ModelMetrics {
  final double? trainMae;
  final double? trainRmse;
  final double? testMae;
  final double? testRmse;
  final double? mape;
  final double? r2Score;
  final int? sampleCount;
  final String? lastDataPoint;

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

  factory ModelMetrics.fromJson(Map<String, dynamic> json) {
    return ModelMetrics(
      trainMae: (json['train_mae'] as num?)?.toDouble(),
      trainRmse: (json['train_rmse'] as num?)?.toDouble(),
      testMae: (json['test_mae'] as num?)?.toDouble(),
      testRmse: (json['test_rmse'] as num?)?.toDouble(),
      mape: (json['mape'] as num?)?.toDouble(),
      r2Score: (json['r2_score'] as num?)?.toDouble(),
      sampleCount: json['sample_count'] as int?,
      lastDataPoint: json['last_data_point'] as String?,
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


/// 模型可解释性数据
class ModelExplainability {
  final Map<String, double> featureImportance;
  final Map<String, String>? featureDescriptions;
  final String? interpretation;

  ModelExplainability({
    required this.featureImportance,
    this.featureDescriptions,
    this.interpretation,
  });

  factory ModelExplainability.fromJson(Map<String, dynamic> json) {
    try {
      // 解析 feature_importance 为 Map<String, double>
      final rawImportance = json['feature_importance'] as Map<String, dynamic>? ?? {};
      final importance = <String, double>{};
      rawImportance.forEach((key, value) {
        if (value is num) {
          importance[key] = value.toDouble();
        }
      });

      // 解析 feature_descriptions
      final rawDescriptions = json['feature_descriptions'] as Map<String, dynamic>?;
      Map<String, String>? descriptions;
      if (rawDescriptions != null) {
        descriptions = rawDescriptions.map((k, v) => MapEntry(k, v.toString()));
      }

      return ModelExplainability(
        featureImportance: importance,
        featureDescriptions: descriptions,
        interpretation: json['interpretation'] as String?,
      );
    } catch (e) {
      throw FormatException('Failed to parse ModelExplainability: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'feature_importance': featureImportance,
      if (featureDescriptions != null) 'feature_descriptions': featureDescriptions,
      if (interpretation != null) 'interpretation': interpretation,
    };
  }

  /// 获取按重要性排序的特征列表
  List<MapEntry<String, double>> get sortedFeatures {
    final entries = featureImportance.entries.toList();
    entries.sort((a, b) => b.value.compareTo(a.value));
    return entries;
  }

  /// 获取最重要的特征
  String? get topFeature {
    if (featureImportance.isEmpty) return null;
    return sortedFeatures.first.key;
  }

  /// 获取最重要特征的重要性百分比
  String get topFeaturePercent {
    if (featureImportance.isEmpty) return 'N/A';
    return '${(sortedFeatures.first.value * 100).toStringAsFixed(1)}%';
  }
}

