part of '../optimization_result.dart';

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
      final rawImportance =
          _toStringDynamicMap(json['feature_importance']) ?? {};
      final importance = <String, double>{};
      rawImportance.forEach((key, value) {
        final parsedValue = _toNullableDouble(value);
        if (parsedValue != null) {
          importance[key] = parsedValue;
        }
      });

      final rawDescriptions = _toStringDynamicMap(json['feature_descriptions']);
      Map<String, String>? descriptions;
      if (rawDescriptions != null) {
        descriptions = rawDescriptions.map((k, v) => MapEntry(k, v.toString()));
      }

      return ModelExplainability(
        featureImportance: importance,
        featureDescriptions: descriptions,
        interpretation: _toNullableString(json['interpretation']),
      );
    } catch (e) {
      throw FormatException('Failed to parse ModelExplainability: $e');
    }
  }

  Map<String, dynamic> toJson() {
    return {
      'feature_importance': featureImportance,
      if (featureDescriptions != null)
        'feature_descriptions': featureDescriptions,
      if (interpretation != null) 'interpretation': interpretation,
    };
  }

  List<MapEntry<String, double>> get sortedFeatures {
    final entries = featureImportance.entries.toList();
    entries.sort((a, b) => b.value.compareTo(a.value));
    return entries;
  }

  String? get topFeature {
    if (featureImportance.isEmpty) return null;
    return sortedFeatures.first.key;
  }

  String get topFeaturePercent {
    if (featureImportance.isEmpty) return 'N/A';
    return '${(sortedFeatures.first.value * 100).toStringAsFixed(1)}%';
  }
}

/// 求解器诊断信息
class SolverDiagnostics {
  final double runtimeSec;
  final double? mipGap;
  final int? nodeCount;
  final int? iterCount;

  SolverDiagnostics({
    required this.runtimeSec,
    this.mipGap,
    this.nodeCount,
    this.iterCount,
  });

  factory SolverDiagnostics.fromJson(Map<String, dynamic> json) {
    return SolverDiagnostics(
      runtimeSec: _toNullableDouble(json['runtime_sec']) ?? 0.0,
      mipGap: _toNullableDouble(json['mip_gap']),
      nodeCount: _toNullableInt(json['node_count']),
      iterCount: _toNullableInt(json['iter_count']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'runtime_sec': runtimeSec,
      if (mipGap != null) 'mip_gap': mipGap,
      if (nodeCount != null) 'node_count': nodeCount,
      if (iterCount != null) 'iter_count': iterCount,
    };
  }

  String get runtimeLabel => '${runtimeSec.toStringAsFixed(2)}s';
}

/// 约束命中统计
class ConstraintHits {
  final int socMinHits;
  final int socMaxHits;
  final int maxChargeHits;
  final int maxDischargeHits;

  ConstraintHits({
    required this.socMinHits,
    required this.socMaxHits,
    required this.maxChargeHits,
    required this.maxDischargeHits,
  });

  factory ConstraintHits.fromJson(Map<String, dynamic> json) {
    int toInt(dynamic value) {
      if (value is int) return value;
      if (value is double) return value.toInt();
      if (value is String) return int.tryParse(value) ?? 0;
      return 0;
    }

    return ConstraintHits(
      socMinHits: toInt(json['soc_min_hits']),
      socMaxHits: toInt(json['soc_max_hits']),
      maxChargeHits: toInt(json['max_charge_hits']),
      maxDischargeHits: toInt(json['max_discharge_hits']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'soc_min_hits': socMinHits,
      'soc_max_hits': socMaxHits,
      'max_charge_hits': maxChargeHits,
      'max_discharge_hits': maxDischargeHits,
    };
  }
}
