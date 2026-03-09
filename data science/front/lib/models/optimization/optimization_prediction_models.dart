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
        targetDate:
            _toNullableString(
              _firstPresent(json, ['target_date', 'targetDate', 'date']),
            ) ??
            '',
        avgLoad: ChartDataPoint._toDouble(
          _firstPresent(json, ['avg_load', 'avgLoad', 'average_load']),
        ),
        peakLoad: ChartDataPoint._toDouble(
          _firstPresent(json, ['peak_load', 'peakLoad', 'max_load']),
        ),
        minLoad: ChartDataPoint._toDouble(
          _firstPresent(json, ['min_load', 'minLoad', 'low_load']),
        ),
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
        capacity: ChartDataPoint._toDouble(
          _firstPresent(json, [
            'capacity',
            'battery_capacity',
            'batteryCapacity',
          ]),
        ),
        maxPower: ChartDataPoint._toDouble(
          _firstPresent(json, [
            'max_power',
            'maxPower',
            'battery_power',
            'batteryPower',
            'power',
          ]),
        ),
        efficiency: ChartDataPoint._toDouble(
          _firstPresent(json, [
            'efficiency',
            'battery_efficiency',
            'batteryEfficiency',
          ]),
        ),
        initialSoc: ChartDataPoint._toDouble(
          _firstPresent(json, [
            'initial_soc',
            'initialSoc',
            'initial_charge',
            'initialCharge',
            'soc',
          ]),
        ),
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
