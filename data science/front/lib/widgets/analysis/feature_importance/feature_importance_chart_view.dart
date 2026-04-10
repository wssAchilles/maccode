part of '../feature_importance_chart.dart';

/// 特征重要性图表组件 (支持滚动和展开/折叠)
///
/// 显示模型预测中各特征的重要性权重，帮助用户理解哪些因素影响了预测结果。
class FeatureImportanceChart extends StatefulWidget {
  const FeatureImportanceChart({
    super.key,
    required this.featureImportance,
    this.featureDescriptions,
    this.interpretation,
    this.defaultVisibleCount = 10,
  });

  /// 特征重要性数据 (特征名 -> 重要性分数)
  final Map<String, double> featureImportance;

  /// 特征描述 (特征名 -> 中文描述)
  final Map<String, String>? featureDescriptions;

  /// 解释文字
  final String? interpretation;

  /// 默认显示的特征数量
  final int defaultVisibleCount;

  @override
  State<FeatureImportanceChart> createState() => _FeatureImportanceChartState();
}

class _FeatureImportanceChartState extends State<FeatureImportanceChart> {
  bool _isExpanded = false;
  bool _didRestoreState = false;
  static const _storageKey = 'feature-importance-expanded';

  static const Map<String, String> defaultDescriptions = {
    'Temperature': '温度',
    'Hour': '小时',
    'Price': '电价',
    'DayOfWeek': '星期',
    'Humidity': '湿度',
    'CloudCover': '云量',
    'WindSpeed': '风速',
    'SolarRadiation': '太阳辐射',
    'IsBusinessDay': '工作日',
    'Load_Lag1': '负荷滞后1h',
    'Load_Lag24': '负荷滞后24h',
    'Load_RollingMean24': '24h滚动均值',
    'Month': '月份',
    'Season': '季节',
    'IsWeekend': '周末',
    'IsHoliday': '节假日',
    'DayOfMonth': '日期',
    'WeekOfYear': '年周数',
    'Temp_x_Season': '温度×季节',
    'Lag24_x_IsWeekend': '滞后24h×周末',
    'Hour_x_IsHoliday': '小时×节假日',
    'Month_Sin': '月份(正弦)',
    'Month_Cos': '月份(余弦)',
    'Hour_Sin': '小时(正弦)',
    'Hour_Cos': '小时(余弦)',
  };

  Color _getColorByRank(int rank, int total) {
    final hue = 210.0 - (rank / total) * 60;
    final saturation = 0.7 - (rank / total) * 0.4;
    final lightness = 0.45 + (rank / total) * 0.15;
    return HSLColor.fromAHSL(1.0, hue, saturation, lightness).toColor();
  }

  String _resolveFeatureName(String key) {
    return widget.featureDescriptions?[key] ?? defaultDescriptions[key] ?? key;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_didRestoreState) {
      return;
    }
    final restored =
        PageStorage.maybeOf(
              context,
            )?.readState(context, identifier: _storageKey)
            as bool?;
    if (restored != null) {
      _isExpanded = restored;
    }
    _didRestoreState = true;
  }

  void _toggleExpanded() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
    PageStorage.maybeOf(
      context,
    )?.writeState(context, _isExpanded, identifier: _storageKey);
  }

  @override
  Widget build(BuildContext context) {
    final sortedEntries = widget.featureImportance.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    if (sortedEntries.isEmpty) {
      return const _FeatureImportanceEmptyState();
    }

    final totalFeatures = sortedEntries.length;
    final defaultVisibleCount = widget.defaultVisibleCount > 0
        ? widget.defaultVisibleCount
        : totalFeatures;
    final visibleCount = _isExpanded
        ? totalFeatures
        : totalFeatures.clamp(0, defaultVisibleCount);

    return _FeatureImportanceCard(
      sortedEntries: sortedEntries,
      displayedEntries: sortedEntries.take(visibleCount).toList(),
      totalFeatures: totalFeatures,
      defaultVisibleCount: defaultVisibleCount,
      isExpanded: _isExpanded,
      interpretation: widget.interpretation,
      resolveFeatureName: _resolveFeatureName,
      colorForRank: _getColorByRank,
      onToggleExpanded: totalFeatures > defaultVisibleCount
          ? _toggleExpanded
          : null,
    );
  }
}
