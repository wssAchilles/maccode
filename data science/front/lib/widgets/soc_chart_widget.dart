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
            Text(
              '🔋 电池电量变化',
              style: TextStyle(
                fontSize: titleFontSize,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '展示24小时内电池电量波动和电价时段',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey,
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
}
