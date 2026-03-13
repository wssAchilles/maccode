/// 优化工作台跳转意图
library;

import 'job_record.dart';
import 'workbench_launch_context.dart';

class OptimizationLaunchIntent {
  const OptimizationLaunchIntent({
    this.initialSoc,
    this.targetDate,
    this.batteryCapacity,
    this.batteryPower,
    this.temperatureAdjust,
    this.resultPayload,
    this.sourceLabel,
    this.context,
  });

  final double? initialSoc;
  final DateTime? targetDate;
  final double? batteryCapacity;
  final double? batteryPower;
  final double? temperatureAdjust;
  final Map<String, dynamic>? resultPayload;
  final String? sourceLabel;
  final WorkbenchLaunchContext? context;

  bool get hasResultPayload =>
      resultPayload != null && resultPayload!.isNotEmpty;

  factory OptimizationLaunchIntent.fromJob(
    JobRecord job, {
    String? sourceLabel,
    WorkbenchLaunchContext? context,
  }) {
    return OptimizationLaunchIntent(
      initialSoc: _asDouble(job.input['initial_soc']),
      targetDate: _parseDateTime(job.input['target_date']),
      batteryCapacity: _asDouble(job.input['battery_capacity']),
      batteryPower: _asDouble(job.input['battery_power']),
      temperatureAdjust: _asDouble(job.input['temperature_adjust']),
      resultPayload: _asMap(job.result),
      sourceLabel: sourceLabel ?? '${job.displayTitle} ${job.jobId.substring(0, 8)}',
      context: context,
    );
  }

  static double? _asDouble(Object? value) {
    if (value is double) {
      return value;
    }
    if (value is num) {
      return value.toDouble();
    }
    if (value is String) {
      return double.tryParse(value);
    }
    return null;
  }

  static DateTime? _parseDateTime(Object? value) {
    if (value is DateTime) {
      return value;
    }
    if (value is String && value.isNotEmpty) {
      return DateTime.tryParse(value);
    }
    return null;
  }

  static Map<String, dynamic>? _asMap(Object? value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }
    return null;
  }
}
