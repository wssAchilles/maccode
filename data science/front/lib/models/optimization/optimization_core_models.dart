part of '../optimization_result.dart';

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
      final optimizationMap = _toStringDynamicMap(
        _firstPresent(json, ['optimization']),
      );
      final predictionMap = _toStringDynamicMap(
        _firstPresent(json, ['prediction']),
      );
      final batteryConfigMap = _toStringDynamicMap(
        _firstPresent(json, ['battery_config', 'batteryConfig']),
      );
      final modelInfoMap = _toStringDynamicMap(
        _firstPresent(json, ['model_info', 'modelInfo']),
      );
      final explainabilityMap = _toStringDynamicMap(
        _firstPresent(json, ['model_explainability', 'modelExplainability']),
      );

      return OptimizationResponse(
        success: _toNullableBool(json['success']) ?? false,
        optimization: optimizationMap != null
            ? OptimizationData.fromJson(optimizationMap)
            : null,
        prediction: predictionMap != null
            ? PredictionInfo.fromJson(predictionMap)
            : null,
        batteryConfig: batteryConfigMap != null
            ? BatteryConfig.fromJson(batteryConfigMap)
            : null,
        modelInfo: modelInfoMap != null
            ? ModelInfo.fromJson(modelInfoMap)
            : null,
        modelExplainability: explainabilityMap != null
            ? ModelExplainability.fromJson(explainabilityMap)
            : null,
        error: _toNullableString(json['error']),
        message: _toNullableString(json['message']),
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
      if (modelExplainability != null)
        'model_explainability': modelExplainability!.toJson(),
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
  final SolverDiagnostics? diagnostics;
  final ConstraintHits? constraintHits;

  OptimizationData({
    required this.status,
    required this.chartData,
    required this.summary,
    required this.strategy,
    this.diagnostics,
    this.constraintHits,
  });

  factory OptimizationData.fromJson(Map<String, dynamic> json) {
    try {
      final chartData = <ChartDataPoint>[];
      final rawChartData = json['chart_data'];
      if (rawChartData is List) {
        for (final item in rawChartData) {
          final itemMap = _toStringDynamicMap(item);
          if (itemMap != null) {
            chartData.add(ChartDataPoint.fromJson(itemMap));
          }
        }
      }

      return OptimizationData(
        status: _toNullableString(json['status']) ?? 'Unknown',
        chartData: chartData,
        summary: OptimizationSummary.fromJson(
          _toStringDynamicMap(json['summary']) ?? const <String, dynamic>{},
        ),
        strategy: OptimizationStrategy.fromJson(
          _toStringDynamicMap(json['strategy']) ?? const <String, dynamic>{},
        ),
        diagnostics: _toStringDynamicMap(json['diagnostics']) != null
            ? SolverDiagnostics.fromJson(
                _toStringDynamicMap(json['diagnostics'])!,
              )
            : null,
        constraintHits: _toStringDynamicMap(json['constraint_hits']) != null
            ? ConstraintHits.fromJson(
                _toStringDynamicMap(json['constraint_hits'])!,
              )
            : null,
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
      if (diagnostics != null) 'diagnostics': diagnostics!.toJson(),
      if (constraintHits != null) 'constraint_hits': constraintHits!.toJson(),
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
  final double batteryAction;
  final double chargePower;
  final double dischargePower;
  final double soc;
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
        hour: _toNullableInt(json['hour']) ?? 0,
        datetime: _toNullableString(json['datetime']) ?? '',
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

  bool get isCharging => batteryAction > 0.01;
  bool get isDischarging => batteryAction < -0.01;
  bool get isIdle => !isCharging && !isDischarging;

  String get batteryStatus {
    if (isCharging) return '充电';
    if (isDischarging) return '放电';
    return '待机';
  }

  String get priceLabel {
    if (price <= 0.3) return '谷时';
    if (price <= 0.6) return '平时';
    return '峰时';
  }

  static double _toDouble(dynamic value) {
    return _toNullableDouble(value) ?? 0.0;
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
        totalCostWithoutBattery: ChartDataPoint._toDouble(
          json['total_cost_without_battery'],
        ),
        totalCostWithBattery: ChartDataPoint._toDouble(
          json['total_cost_with_battery'],
        ),
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

  double get cycleEfficiency {
    if (totalCharged == 0) return 0.0;
    return (totalDischarged / totalCharged) * 100;
  }

  String get savingsFormatted => '${savings.toStringAsFixed(2)} 元';
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
        chargingHours: _toIntList(json['charging_hours']) ?? [],
        dischargingHours: _toIntList(json['discharging_hours']) ?? [],
        chargingCount: _toNullableInt(json['charging_count']) ?? 0,
        dischargingCount: _toNullableInt(json['discharging_count']) ?? 0,
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

  String get chargingHoursFormatted {
    if (chargingHours.isEmpty) return '无';
    return chargingHours
        .map((h) => '${h.toString().padLeft(2, '0')}:00')
        .join(', ');
  }

  String get dischargingHoursFormatted {
    if (dischargingHours.isEmpty) return '无';
    return dischargingHours
        .map((h) => '${h.toString().padLeft(2, '0')}:00')
        .join(', ');
  }
}
