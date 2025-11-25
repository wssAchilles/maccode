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
  final String? error;
  final String? message;

  OptimizationResponse({
    required this.success,
    this.optimization,
    this.prediction,
    this.batteryConfig,
    this.modelInfo,
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
  final Map<String, dynamic>? metrics;
  final int? trainingSamples;
  final String? dataSource;
  final String? status;
  final String? message;

  ModelInfo({
    required this.modelType,
    this.modelVersion,
    this.trainedAt,
    this.metrics,
    this.trainingSamples,
    this.dataSource,
    this.status,
    this.message,
  });

  factory ModelInfo.fromJson(Map<String, dynamic> json) {
    try {
      return ModelInfo(
        modelType: json['model_type'] as String? ?? 'Unknown',
        modelVersion: json['model_version'] as String?,
        trainedAt: json['trained_at'] as String?,
        metrics: json['metrics'] as Map<String, dynamic>?,
        trainingSamples: json['training_samples'] as int?,
        dataSource: json['data_source'] as String?,
        status: json['status'] as String?,
        message: json['message'] as String?,
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
      if (metrics != null) 'metrics': metrics,
      if (trainingSamples != null) 'training_samples': trainingSamples,
      if (dataSource != null) 'data_source': dataSource,
      if (status != null) 'status': status,
      if (message != null) 'message': message,
    };
  }

  /// 是否有效
  bool get isValid => status == 'active';

  /// 测试集MAE
  double? get testMae {
    if (metrics == null) return null;
    final mae = metrics!['test_mae'];
    if (mae is num) return mae.toDouble();
    return null;
  }

  /// 测试集RMSE
  double? get testRmse {
    if (metrics == null) return null;
    final rmse = metrics!['test_rmse'];
    if (rmse is num) return rmse.toDouble();
    return null;
  }

  /// 格式化训练时间
  String get trainedAtFormatted {
    if (trainedAt == null) return '未知';
    try {
      final dt = DateTime.parse(trainedAt!);
      return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      return trainedAt!;
    }
  }

  /// 格式化MAE
  String get maeFormatted {
    final mae = testMae;
    if (mae == null) return 'N/A';
    return '${mae.toStringAsFixed(2)} kW';
  }

  /// 格式化RMSE
  String get rmseFormatted {
    final rmse = testRmse;
    if (rmse == null) return 'N/A';
    return '${rmse.toStringAsFixed(2)} kW';
  }
}
