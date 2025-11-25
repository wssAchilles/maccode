/// 电池电量变化图表
/// 展示 SOC 趋势和电价时段
library;

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/optimization_result.dart';
import '../utils/responsive_helper.dart';

class SocChartWidget extends StatelessWidget {
  final List<ChartDataPoint> chartData;

  const SocChartWidget({
    super.key,
    required this.chartData,
  });

  @override
  Widget build(BuildContext context) {
    // 响应式图表高度
    final chartHeight = ResponsiveHelper.getResponsiveValue(
      context,
      mobile: 250.0,
      tablet: 300.0,
      desktop: 350.0,
    );
    
    // 响应式字体大小
    final titleFontSize = ResponsiveHelper.getResponsiveFontSize(
      context,
      mobile: 16.0,
      tablet: 18.0,
      desktop: 20.0,
    );
    
    return Card(
      elevation: 4,
      child: Padding(
        padding: ResponsiveHelper.getCardPadding(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  '🔋 电池电量变化',
                  style: TextStyle(
                    fontSize: titleFontSize,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 8),
                // 实时状态指示
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getOverallStatusColor().withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _getOverallStatus(),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: _getOverallStatusColor(),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            // 策略摘要
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.purple.withOpacity(0.05),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.purple.withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  Icon(Icons.lightbulb_outline, size: 16, color: Colors.purple[600]),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _getStrategyExplanation(),
                      style: TextStyle(fontSize: 12, color: Colors.grey[700]),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: chartHeight,
              child: LineChart(
                _buildLineChartData(context),
              ),
            ),
            const SizedBox(height: 16),
            _buildLegend(context),
          ],
        ),
      ),
    );
  }

  LineChartData _buildLineChartData(BuildContext context) {
    return LineChartData(
      gridData: FlGridData(
        show: true,
        drawVerticalLine: true,
        horizontalInterval: 20,
        verticalInterval: 4,
        getDrawingHorizontalLine: (value) {
          return FlLine(
            color: Colors.grey.withOpacity(0.2),
            strokeWidth: 1,
          );
        },
        getDrawingVerticalLine: (value) {
          return FlLine(
            color: Colors.grey.withOpacity(0.2),
            strokeWidth: 1,
          );
        },
      ),
      titlesData: FlTitlesData(
        show: true,
        rightTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        topTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 30,
            interval: 4,
            getTitlesWidget: (value, meta) {
              final hour = value.toInt();
              if (hour % 4 == 0 && hour >= 0 && hour <= 23) {
                return Text(
                  '${hour.toString().padLeft(2, '0')}:00',
                  style: const TextStyle(
                    fontSize: 10,
                    color: Colors.grey,
                  ),
                );
              }
              return const Text('');
            },
          ),
        ),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            interval: 20,
            reservedSize: 40,
            getTitlesWidget: (value, meta) {
              return Text(
                '${value.toInt()}%',
                style: const TextStyle(
                  fontSize: 10,
                  color: Colors.grey,
                ),
              );
            },
          ),
        ),
      ),
      borderData: FlBorderData(
        show: true,
        border: Border.all(color: Colors.grey.withOpacity(0.3)),
      ),
      minX: 0,
      maxX: 23,
      minY: 0,
      maxY: 100,
      lineBarsData: [
        // SOC 曲线 (紫色平滑曲线)
        LineChartBarData(
          spots: chartData.asMap().entries.map((entry) {
            return FlSpot(entry.key.toDouble(), entry.value.soc);
          }).toList(),
          isCurved: true,
          color: Colors.purple,
          barWidth: 3,
          isStrokeCapRound: true,
          dotData: FlDotData(
            show: true,
            getDotPainter: (spot, percent, barData, index) {
              final data = chartData[index];
              Color dotColor = Colors.purple;
              
              // 根据电池状态改变点的颜色
              if (data.isCharging) {
                dotColor = Colors.green;
              } else if (data.isDischarging) {
                dotColor = Colors.red;
              }
              
              return FlDotCirclePainter(
                radius: 3,
                color: dotColor,
                strokeWidth: 1,
                strokeColor: Colors.white,
              );
            },
          ),
          belowBarData: BarAreaData(
            show: true,
            gradient: LinearGradient(
              colors: [
                Colors.purple.withOpacity(0.3),
                Colors.purple.withOpacity(0.1),
              ],
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
            ),
          ),
        ),
      ],
      // 绘制电价时段背景
      rangeAnnotations: RangeAnnotations(
        horizontalRangeAnnotations: _buildPriceRanges(),
      ),
      lineTouchData: LineTouchData(
        enabled: true,
        touchTooltipData: LineTouchTooltipData(
          getTooltipColor: (LineBarSpot spot) =>
              Colors.purple.withOpacity(0.8),
          getTooltipItems: (List<LineBarSpot> touchedBarSpots) {
            return touchedBarSpots.map((barSpot) {
              final hour = barSpot.x.toInt();
              if (hour >= 0 && hour < chartData.length) {
                final data = chartData[hour];
                return LineTooltipItem(
                  '${hour.toString().padLeft(2, '0')}:00\n',
                  const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                  children: [
                    TextSpan(
                      text: 'SOC: ${data.soc.toStringAsFixed(1)}%\n',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                      ),
                    ),
                    TextSpan(
                      text: '${data.priceLabel} (${data.price} 元/kWh)\n',
                      style: TextStyle(
                        color: _getPriceColor(data.price),
                        fontSize: 12,
                      ),
                    ),
                    TextSpan(
                      text: data.batteryStatus,
                      style: TextStyle(
                        color: data.isCharging
                            ? Colors.green
                            : data.isDischarging
                                ? Colors.red
                                : Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  ],
                );
              }
              return null;
            }).toList();
          },
        ),
      ),
    );
  }

  List<HorizontalRangeAnnotation> _buildPriceRanges() {
    final ranges = <HorizontalRangeAnnotation>[];
    
    // 谷时时段 (00:00-08:00, 22:00-24:00) - 绿色背景
    ranges.add(
      HorizontalRangeAnnotation(
        y1: 0,
        y2: 100,
        color: Colors.green.withOpacity(0.05),
      ),
    );
    
    // 这里我们用垂直区域来表示时段，但 fl_chart 不直接支持垂直范围
    // 所以我们使用 extraLinesData 来标记时段分界
    
    return ranges;
  }

  Color _getPriceColor(double price) {
    if (price <= 0.3) return Colors.green;
    if (price <= 0.6) return Colors.orange;
    return Colors.red;
  }

  Widget _buildLegend(BuildContext context) {
    // 图例始终使用 Wrap 以适应不同屏幕
    return Wrap(
      spacing: ResponsiveHelper.getResponsiveValue(context, mobile: 12.0, tablet: 16.0),
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: [
        _buildLegendItem(Colors.purple, 'SOC 趋势'),
        _buildLegendItem(Colors.green.withOpacity(0.3), '谷时 (0.3元)', isBackground: true),
        _buildLegendItem(Colors.orange.withOpacity(0.3), '平时 (0.6元)', isBackground: true),
        _buildLegendItem(Colors.red.withOpacity(0.3), '峰时 (1.0元)', isBackground: true),
      ],
    );
  }

  Widget _buildLegendItem(Color color, String label, {bool isBackground = false}) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: isBackground ? 16 : 20,
          height: isBackground ? 12 : 3,
          decoration: BoxDecoration(
            color: color,
            borderRadius: isBackground ? BorderRadius.circular(2) : null,
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: Colors.grey[700],
          ),
        ),
      ],
    );
  }
  
  /// 获取整体状态
  String _getOverallStatus() {
    final chargingHours = chartData.where((d) => d.isCharging).length;
    final dischargingHours = chartData.where((d) => d.isDischarging).length;
    
    if (chargingHours > dischargingHours) {
      return '📥 充电为主';
    } else if (dischargingHours > chargingHours) {
      return '📤 放电为主';
    } else {
      return '⚖️ 平衡模式';
    }
  }
  
  /// 获取状态颜色
  Color _getOverallStatusColor() {
    final chargingHours = chartData.where((d) => d.isCharging).length;
    final dischargingHours = chartData.where((d) => d.isDischarging).length;
    
    if (chargingHours > dischargingHours) {
      return Colors.green;
    } else if (dischargingHours > chargingHours) {
      return Colors.orange;
    } else {
      return Colors.blue;
    }
  }
  
  /// 生成策略解释 (方案二核心功能)
  String _getStrategyExplanation() {
    // 找到主要充电时段
    final chargingHours = <int>[];
    final dischargingHours = <int>[];
    
    for (int i = 0; i < chartData.length; i++) {
      if (chartData[i].isCharging) {
        chargingHours.add(i);
      } else if (chartData[i].isDischarging) {
        dischargingHours.add(i);
      }
    }
    
    // 找到连续时段
    String chargeRange = _formatHourRanges(chargingHours);
    String dischargeRange = _formatHourRanges(dischargingHours);
    
    if (chargingHours.isEmpty && dischargingHours.isEmpty) {
      return '当前策略: 电池保持待机状态';
    }
    
    final buffer = StringBuffer('策略: ');
    
    if (chargingHours.isNotEmpty) {
      buffer.write('$chargeRange 低价充电');
    }
    
    if (chargingHours.isNotEmpty && dischargingHours.isNotEmpty) {
      buffer.write(' → ');
    }
    
    if (dischargingHours.isNotEmpty) {
      buffer.write('$dischargeRange 高峰放电');
    }
    
    return buffer.toString();
  }
  
  /// 格式化小时范围
  String _formatHourRanges(List<int> hours) {
    if (hours.isEmpty) return '';
    
    hours.sort();
    
    // 简化：只显示第一个和最后一个
    if (hours.length == 1) {
      return '${hours.first}:00';
    }
    
    // 检查是否连续
    bool isContinuous = true;
    for (int i = 1; i < hours.length; i++) {
      if (hours[i] - hours[i - 1] > 1) {
        isContinuous = false;
        break;
      }
    }
    
    if (isContinuous) {
      return '${hours.first}:00-${hours.last + 1}:00';
    } else {
      // 显示主要时段
      return '${hours.first}:00-${hours.last + 1}:00';
    }
  }
}
