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
      return OptimizationResponse(
        success: json['success'] as bool? ?? false,
        optimization: json['optimization'] != null
            ? OptimizationData.fromJson(
                json['optimization'] as Map<String, dynamic>,
              )
            : null,
        prediction: json['prediction'] != null
            ? PredictionInfo.fromJson(
                json['prediction'] as Map<String, dynamic>,
              )
            : null,
        batteryConfig: json['battery_config'] != null
            ? BatteryConfig.fromJson(
                json['battery_config'] as Map<String, dynamic>,
              )
            : null,
        modelInfo: json['model_info'] != null
            ? ModelInfo.fromJson(json['model_info'] as Map<String, dynamic>)
            : null,
        modelExplainability: json['model_explainability'] != null
            ? ModelExplainability.fromJson(
                json['model_explainability'] as Map<String, dynamic>,
              )
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
      return OptimizationData(
        status: json['status'] as String? ?? 'Unknown',
        chartData:
            (json['chart_data'] as List<dynamic>?)
                ?.map(
                  (item) =>
                      ChartDataPoint.fromJson(item as Map<String, dynamic>),
                )
                .toList() ??
            [],
        summary: OptimizationSummary.fromJson(
          json['summary'] as Map<String, dynamic>? ?? {},
        ),
        strategy: OptimizationStrategy.fromJson(
          json['strategy'] as Map<String, dynamic>? ?? {},
        ),
        diagnostics: json['diagnostics'] != null
            ? SolverDiagnostics.fromJson(
                json['diagnostics'] as Map<String, dynamic>,
              )
            : null,
        constraintHits: json['constraint_hits'] != null
            ? ConstraintHits.fromJson(
                json['constraint_hits'] as Map<String, dynamic>,
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
        chargingHours:
            (json['charging_hours'] as List<dynamic>?)
                ?.map((e) => e as int)
                .toList() ??
            [],
        dischargingHours:
            (json['discharging_hours'] as List<dynamic>?)
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
