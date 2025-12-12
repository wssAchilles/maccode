import 'package:flutter/material.dart';

/// 特征重要性图表组件 (支持滚动和展开/折叠)
/// 
/// 显示模型预测中各特征的重要性权重，
/// 帮助用户理解哪些因素影响了预测结果
class FeatureImportanceChart extends StatefulWidget {
  /// 特征重要性数据 (特征名 -> 重要性分数)
  final Map<String, double> featureImportance;
  
  /// 特征描述 (特征名 -> 中文描述)
  final Map<String, String>? featureDescriptions;
  
  /// 解释文字
  final String? interpretation;
  
  /// 默认显示的特征数量
  final int defaultVisibleCount;

  const FeatureImportanceChart({
    super.key,
    required this.featureImportance,
    this.featureDescriptions,
    this.interpretation,
    this.defaultVisibleCount = 10,
  });

  @override
  State<FeatureImportanceChart> createState() => _FeatureImportanceChartState();
}

class _FeatureImportanceChartState extends State<FeatureImportanceChart> {
  bool _isExpanded = false;
  
  // 特征中文名称映射 (扩展版)
  static const Map<String, String> defaultDescriptions = {
    // 基础特征
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
    // 增强特征
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

  // 根据重要性排名生成渐变色
  Color _getColorByRank(int rank, int total) {
    // 高重要性: 蓝色 -> 中等: 青色 -> 低重要性: 灰色
    final hue = 210.0 - (rank / total) * 60; // 210 (蓝) -> 150 (青)
    final saturation = 0.7 - (rank / total) * 0.4; // 0.7 -> 0.3
    final lightness = 0.45 + (rank / total) * 0.15; // 0.45 -> 0.6
    return HSLColor.fromAHSL(1.0, hue, saturation, lightness).toColor();
  }

  @override
  Widget build(BuildContext context) {
    final sortedEntries = widget.featureImportance.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    
    final totalFeatures = sortedEntries.length;
    final visibleCount = _isExpanded 
        ? totalFeatures 
        : totalFeatures.clamp(0, widget.defaultVisibleCount);
    final displayedEntries = sortedEntries.take(visibleCount).toList();
    final maxValue = sortedEntries.isNotEmpty ? sortedEntries.first.value : 1.0;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题栏
          Row(
            children: [
              Icon(
                Icons.insights,
                color: Theme.of(context).colorScheme.primary,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                '特征重要性分析',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              // 特征数量指示
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '共 $totalFeatures 个特征',
                  style: TextStyle(
                    fontSize: 11,
                    color: Theme.of(context).colorScheme.onPrimaryContainer,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // 水平条形图列表 (可滚动)
          ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: _isExpanded ? 500 : 320, // 展开时更高
            ),
            child: SingleChildScrollView(
              child: Column(
                children: displayedEntries.asMap().entries.map((entry) {
                  final index = entry.key;
                  final data = entry.value;
                  final featureName = defaultDescriptions[data.key] ?? data.key;
                  final percentage = data.value * 100;
                  final barWidthRatio = maxValue > 0 ? data.value / maxValue : 0.0;
                  final color = _getColorByRank(index, totalFeatures);
                  
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      children: [
                        // 排名
                        SizedBox(
                          width: 24,
                          child: Text(
                            '${index + 1}',
                            style: TextStyle(
                              fontSize: 11,
                              color: index < 3 
                                  ? Theme.of(context).colorScheme.primary 
                                  : Colors.grey,
                              fontWeight: index < 3 ? FontWeight.bold : FontWeight.normal,
                            ),
                          ),
                        ),
                        // 特征名称
                        SizedBox(
                          width: 100,
                          child: Text(
                            featureName,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        // 条形图
                        Expanded(
                          child: Stack(
                            children: [
                              // 背景
                              Container(
                                height: 20,
                                decoration: BoxDecoration(
                                  color: Colors.grey.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                              ),
                              // 前景条
                              FractionallySizedBox(
                                widthFactor: barWidthRatio,
                                child: Container(
                                  height: 20,
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: [
                                        color.withOpacity(0.8),
                                        color,
                                      ],
                                    ),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        // 百分比
                        SizedBox(
                          width: 50,
                          child: Text(
                            '${percentage.toStringAsFixed(1)}%',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: index < 3 
                                  ? Theme.of(context).colorScheme.primary 
                                  : Colors.grey[700],
                            ),
                            textAlign: TextAlign.right,
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          
          // 展开/折叠按钮
          if (totalFeatures > widget.defaultVisibleCount) ...[
            const SizedBox(height: 8),
            Center(
              child: TextButton.icon(
                onPressed: () {
                  setState(() {
                    _isExpanded = !_isExpanded;
                  });
                },
                icon: Icon(
                  _isExpanded ? Icons.expand_less : Icons.expand_more,
                  size: 18,
                ),
                label: Text(
                  _isExpanded 
                      ? '收起 (显示前 ${widget.defaultVisibleCount} 个)'
                      : '展开全部 (${totalFeatures - widget.defaultVisibleCount} 个更多)',
                  style: const TextStyle(fontSize: 12),
                ),
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                ),
              ),
            ),
          ],
          
          // 解释文字
          if (widget.interpretation != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.lightbulb_outline,
                    color: Theme.of(context).colorScheme.primary,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      widget.interpretation!,
                      style: TextStyle(
                        fontSize: 13,
                        color: Theme.of(context).colorScheme.onSurface,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          
          // 顶部特征摘要
          const SizedBox(height: 12),
          _buildTopFeaturesSummary(sortedEntries.take(3).toList()),
        ],
      ),
    );
  }
  
  /// 构建顶部特征摘要
  Widget _buildTopFeaturesSummary(List<MapEntry<String, double>> topFeatures) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.blue.withOpacity(0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.star, size: 14, color: Colors.amber[700]),
              const SizedBox(width: 4),
              const Text(
                '最重要的特征',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: topFeatures.asMap().entries.map((entry) {
              final rank = entry.key + 1;
              final feature = entry.value;
              final name = defaultDescriptions[feature.key] ?? feature.key;
              final color = rank == 1 
                  ? Colors.amber[700]! 
                  : rank == 2 
                      ? Colors.grey[600]! 
                      : Colors.brown[400]!;
              
              return Chip(
                avatar: CircleAvatar(
                  backgroundColor: color,
                  radius: 10,
                  child: Text(
                    '$rank',
                    style: const TextStyle(
                      fontSize: 10,
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                label: Text(
                  '$name (${(feature.value * 100).toStringAsFixed(1)}%)',
                  style: const TextStyle(fontSize: 11),
                ),
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                padding: const EdgeInsets.symmetric(horizontal: 4),
                visualDensity: VisualDensity.compact,
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
