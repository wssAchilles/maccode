/// 电网交互策略图表
/// 展示负载、电网功率和电池充放电
library;

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../models/optimization_result.dart';
import '../utils/responsive_helper.dart';

class PowerChartWidget extends StatelessWidget {
  final List<ChartDataPoint> chartData;

  const PowerChartWidget({
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
              '⚡ 电网交互策略',
              style: TextStyle(
                fontSize: titleFontSize,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '展示负载、电网功率和电池充放电策略',
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
        horizontalInterval: 50,
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
            interval: 50,
            reservedSize: 40,
            getTitlesWidget: (value, meta) {
              return Text(
                '${value.toInt()}',
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
      minY: _getMinY(),
      maxY: _getMaxY(),
      lineBarsData: [
        // 线条 1: 原始负载 (灰色虚线)
        LineChartBarData(
          spots: chartData.asMap().entries.map((entry) {
            return FlSpot(entry.key.toDouble(), entry.value.load);
          }).toList(),
          isCurved: true,
          color: Colors.grey,
          barWidth: 2,
          isStrokeCapRound: true,
          dotData: const FlDotData(show: false),
          belowBarData: BarAreaData(show: false),
          dashArray: [5, 5], // 虚线
        ),
        // 线条 2: 电网功率 (蓝色实线)
        LineChartBarData(
          spots: chartData.asMap().entries.map((entry) {
            return FlSpot(entry.key.toDouble(), entry.value.gridPower);
          }).toList(),
          isCurved: true,
          color: Colors.blue,
          barWidth: 3,
          isStrokeCapRound: true,
          dotData: const FlDotData(show: false),
          belowBarData: BarAreaData(
            show: true,
            color: Colors.blue.withOpacity(0.1),
          ),
        ),
      ],
      // 添加电池充放电的标记
      extraLinesData: ExtraLinesData(
        horizontalLines: [
          HorizontalLine(
            y: 0,
            color: Colors.black.withOpacity(0.3),
            strokeWidth: 1,
            dashArray: [5, 5],
          ),
        ],
      ),
      lineTouchData: LineTouchData(
        enabled: true,
        touchTooltipData: LineTouchTooltipData(
          getTooltipColor: (LineBarSpot spot) =>
              Colors.blueGrey.withOpacity(0.8),
          getTooltipItems: (List<LineBarSpot> touchedBarSpots) {
            return touchedBarSpots.map((barSpot) {
              final hour = barSpot.x.toInt();
              if (hour >= 0 && hour < chartData.length) {
                final data = chartData[hour];
                final label = barSpot.barIndex == 0 ? '负载' : '电网';
                return LineTooltipItem(
                  '${hour.toString().padLeft(2, '0')}:00\n',
                  const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                  children: [
                    TextSpan(
                      text: '$label: ${barSpot.y.toStringAsFixed(1)} kW\n',
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                    TextSpan(
                      text: '电池: ${data.batteryStatus}',
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

  double _getMinY() {
    double minLoad = chartData.map((e) => e.load).reduce((a, b) => a < b ? a : b);
    double minGrid = chartData.map((e) => e.gridPower).reduce((a, b) => a < b ? a : b);
    return (minLoad < minGrid ? minLoad : minGrid) * 0.9;
  }

  double _getMaxY() {
    double maxLoad = chartData.map((e) => e.load).reduce((a, b) => a > b ? a : b);
    double maxGrid = chartData.map((e) => e.gridPower).reduce((a, b) => a > b ? a : b);
    return (maxLoad > maxGrid ? maxLoad : maxGrid) * 1.1;
  }

  Widget _buildLegend(BuildContext context) {
    final isMobile = ResponsiveHelper.isMobile(context);
    
    if (isMobile) {
      // 移动端：垂直布局或换行
      return Wrap(
        spacing: 12,
        runSpacing: 8,
        alignment: WrapAlignment.center,
        children: [
          _buildLegendItem(Colors.grey, '原始负载', isDashed: true),
          _buildLegendItem(Colors.blue, '电网功率'),
          _buildLegendItem(Colors.green, '充电', isSmall: true),
          _buildLegendItem(Colors.red, '放电', isSmall: true),
        ],
      );
    } else {
      // 桌面端：水平布局
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildLegendItem(Colors.grey, '原始负载', isDashed: true),
          const SizedBox(width: 16),
          _buildLegendItem(Colors.blue, '电网功率'),
          const SizedBox(width: 16),
          _buildLegendItem(Colors.green, '充电', isSmall: true),
          const SizedBox(width: 8),
          _buildLegendItem(Colors.red, '放电', isSmall: true),
        ],
      );
    }
  }

  Widget _buildLegendItem(Color color, String label,
      {bool isDashed = false, bool isSmall = false}) {
    return Row(
      children: [
        Container(
          width: isSmall ? 12 : 20,
          height: isSmall ? 12 : 3,
          decoration: BoxDecoration(
            color: isDashed ? Colors.transparent : color,
            border: isDashed ? Border.all(color: color, width: 2) : null,
            borderRadius: isSmall ? BorderRadius.circular(2) : null,
          ),
          child: isDashed
              ? CustomPaint(
                  painter: _DashedLinePainter(color: color),
                )
              : null,
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: isSmall ? 11 : 12,
            color: Colors.grey[700],
          ),
        ),
      ],
    );
  }
}

class _DashedLinePainter extends CustomPainter {
  final Color color;

  _DashedLinePainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    const dashWidth = 3.0;
    const dashSpace = 2.0;
    double startX = 0;

    while (startX < size.width) {
      canvas.drawLine(
        Offset(startX, size.height / 2),
        Offset(startX + dashWidth, size.height / 2),
        paint,
      );
      startX += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
