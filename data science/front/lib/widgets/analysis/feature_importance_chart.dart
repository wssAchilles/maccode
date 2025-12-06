import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

/// 特征重要性图表组件
/// 
/// 显示模型预测中各特征的重要性权重，
/// 帮助用户理解哪些因素影响了预测结果
class FeatureImportanceChart extends StatelessWidget {
  /// 特征重要性数据 (特征名 -> 重要性分数)
  final Map<String, double> featureImportance;
  
  /// 特征描述 (特征名 -> 中文描述)
  final Map<String, String>? featureDescriptions;
  
  /// 解释文字
  final String? interpretation;

  const FeatureImportanceChart({
    super.key,
    required this.featureImportance,
    this.featureDescriptions,
    this.interpretation,
  });

  // 特征颜色映射
  static const Map<String, Color> featureColors = {
    'Temperature': Color(0xFFE53935), // 红色 - 温度
    'Hour': Color(0xFF1E88E5),        // 蓝色 - 小时
    'Price': Color(0xFF43A047),       // 绿色 - 电价
    'DayOfWeek': Color(0xFFFF9800),   // 橙色 - 星期
  };

  // 特征中文名称
  static const Map<String, String> defaultDescriptions = {
    'Temperature': '温度',
    'Hour': '小时',
    'Price': '电价',
    'DayOfWeek': '星期',
  };

  @override
  Widget build(BuildContext context) {
    final sortedEntries = featureImportance.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

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
          // 标题
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
            ],
          ),
          const SizedBox(height: 16),
          
          // 水平条形图
          SizedBox(
            height: sortedEntries.length * 50.0,
            child: BarChart(
              BarChartData(
                alignment: BarChartAlignment.spaceAround,
                maxY: 1.0,
                barTouchData: BarTouchData(
                  enabled: true,
                  touchTooltipData: BarTouchTooltipData(
                    getTooltipItem: (group, groupIndex, rod, rodIndex) {
                      final entry = sortedEntries[group.x.toInt()];
                      final name = defaultDescriptions[entry.key] ?? entry.key;
                      return BarTooltipItem(
                        '$name\n${(entry.value * 100).toStringAsFixed(1)}%',
                        const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      );
                    },
                  ),
                ),
                titlesData: FlTitlesData(
                  show: true,
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 32, // 确保有足够空间显示带 padding 的汉字
                      getTitlesWidget: (value, meta) {
                        if (value.toInt() >= sortedEntries.length) {
                          return const SizedBox.shrink();
                        }
                        final entry = sortedEntries[value.toInt()];
                        final name = defaultDescriptions[entry.key] ?? entry.key;
                        return Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            name,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 40,
                      getTitlesWidget: (value, meta) {
                        return Text(
                          '${(value * 100).toInt()}%',
                          style: const TextStyle(fontSize: 10),
                        );
                      },
                    ),
                  ),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: false),
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  horizontalInterval: 0.25,
                ),
                barGroups: sortedEntries.asMap().entries.map((entry) {
                  final index = entry.key;
                  final data = entry.value;
                  final color = featureColors[data.key] ?? Colors.grey;
                  
                  return BarChartGroupData(
                    x: index,
                    barRods: [
                      BarChartRodData(
                        toY: data.value,
                        color: color,
                        width: 24,
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(4),
                          topRight: Radius.circular(4),
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
          ),
          
          // 解释文字
          if (interpretation != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.lightbulb_outline,
                    color: Theme.of(context).colorScheme.primary,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      interpretation!,
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
          
          // 图例
          const SizedBox(height: 12),
          Wrap(
            spacing: 16,
            runSpacing: 8,
            children: sortedEntries.map((entry) {
              final color = featureColors[entry.key] ?? Colors.grey;
              final name = defaultDescriptions[entry.key] ?? entry.key;
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 12,
                    height: 12,
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '$name: ${(entry.value * 100).toStringAsFixed(1)}%',
                    style: const TextStyle(fontSize: 11),
                  ),
                ],
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
