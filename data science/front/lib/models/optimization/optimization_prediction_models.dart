part of '../optimization_result.dart';

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

  String get capacityFormatted => '${capacity.toStringAsFixed(1)} kWh';
  String get powerFormatted => '${maxPower.toStringAsFixed(1)} kW';
  String get efficiencyFormatted => '${(efficiency * 100).toStringAsFixed(0)}%';
}
