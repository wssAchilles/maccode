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
            Row(
              children: [
                Text(
                  '⚡ 电网交互策略',
                  style: TextStyle(
                    fontSize: titleFontSize,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.purple[100],
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.psychology, size: 14, color: Colors.purple[700]),
                      const SizedBox(width: 4),
                      Text(
                        'AI 预测驱动',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: Colors.purple[700],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              '基于随机森林模型预测的24小时负载 + Gurobi优化的充放电策略',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey,
                fontWeight: FontWeight.w500,
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
            interval: _getYAxisInterval(),
            reservedSize: 65,  // 增加左侧预留空间，适应大数值
            getTitlesWidget: (value, meta) {
              // 格式化大数值：超过1000显示为 "XXk"
              String label;
              if (value.abs() >= 1000) {
                label = '${(value / 1000).toStringAsFixed(1)}k';
              } else {
                label = value.toInt().toString();
              }
              return Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 10,
                    color: Colors.grey,
                  ),
                  textAlign: TextAlign.right,
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
        // 线条 1: 原始负载 (灰色虚线) - AI 预测
        LineChartBarData(
          spots: chartData.asMap().entries.map((entry) {
            return FlSpot(entry.key.toDouble(), entry.value.load);
          }).toList(),
          isCurved: true,
          color: Colors.grey[600]!,
          barWidth: 2,
          isStrokeCapRound: true,
          dotData: const FlDotData(show: false),
          belowBarData: BarAreaData(show: false),
          dashArray: [5, 5], // 虚线
        ),
        // 线条 2: 优化后电网功率 (蓝色实线)
        LineChartBarData(
          spots: chartData.asMap().entries.map((entry) {
            return FlSpot(entry.key.toDouble(), entry.value.gridPower);
          }).toList(),
          isCurved: true,
          gradient: LinearGradient(
            colors: [Colors.blue[400]!, Colors.blue[700]!],
          ),
          barWidth: 3,
          isStrokeCapRound: true,
          dotData: FlDotData(
            show: true,
            getDotPainter: (spot, percent, barData, index) {
              final data = chartData[index];
              // 根据电池状态显示不同颜色的点
              Color dotColor = Colors.blue;
              if (data.isCharging) {
                dotColor = Colors.green; // 充电 = 填谷
              } else if (data.isDischarging) {
                dotColor = Colors.orange; // 放电 = 削峰
              }
              return FlDotCirclePainter(
                radius: 3,
                color: dotColor,
                strokeWidth: 0,
              );
            },
          ),
          belowBarData: BarAreaData(
            show: true,
            gradient: LinearGradient(
              colors: [
                Colors.blue.withOpacity(0.2),
                Colors.blue.withOpacity(0.05),
              ],
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
            ),
          ),
        ),
      ],
      // 显示削峰填谷区域（两条线之间的差异）
      betweenBarsData: [
        BetweenBarsData(
          fromIndex: 0, // 原始负载
          toIndex: 1,   // 电网功率
          color: _getDifferenceColor(),
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
  
  /// 根据数据范围动态计算 Y 轴间隔
  double _getYAxisInterval() {
    final range = _getMaxY() - _getMinY();
    if (range > 10000) return 5000;
    if (range > 5000) return 2000;
    if (range > 1000) return 500;
    if (range > 500) return 100;
    return 50;
  }
  
  /// 获取削峰填谷区域的颜色
  Color _getDifferenceColor() {
    // 计算总体差异来决定颜色
    double totalCharging = 0;
    double totalDischarging = 0;
    
    for (final data in chartData) {
      if (data.isCharging) {
        totalCharging += data.chargePower;
      } else if (data.isDischarging) {
        totalDischarging += data.dischargePower;
      }
    }
    
    // 混合颜色：充电多用绿色，放电多用橙色
    if (totalCharging > totalDischarging) {
      return Colors.green.withOpacity(0.15);
    } else {
      return Colors.orange.withOpacity(0.15);
    }
  }

  Widget _buildLegend(BuildContext context) {
    final isMobile = ResponsiveHelper.isMobile(context);
    
    // 计算节省量用于显示
    final totalSaving = chartData.fold<double>(0, (sum, d) => sum + (d.load - d.gridPower).abs());
    
    if (isMobile) {
      // 移动端：垂直布局或换行
      return Column(
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              _buildLegendItem(Colors.grey, 'AI 预测负载', isDashed: true, hasAiTag: true),
              _buildLegendItem(Colors.blue, '优化后电网'),
              _buildLegendItem(Colors.green, '充电(填谷)', isSmall: true),
              _buildLegendItem(Colors.orange, '放电(削峰)', isSmall: true),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              '⚡ 阴影区域 = 削峰填谷效果 (${totalSaving.toStringAsFixed(0)} kWh 优化)',
              style: TextStyle(fontSize: 11, color: Colors.green[700], fontWeight: FontWeight.w500),
            ),
          ),
        ],
      );
    } else {
      // 桌面端：水平布局
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildLegendItem(Colors.grey, 'AI 预测负载', isDashed: true, hasAiTag: true),
          const SizedBox(width: 16),
          _buildLegendItem(Colors.blue, '优化后电网'),
          const SizedBox(width: 16),
          _buildLegendItem(Colors.green, '充电(填谷)', isSmall: true),
          const SizedBox(width: 8),
          _buildLegendItem(Colors.orange, '放电(削峰)', isSmall: true),
          const SizedBox(width: 16),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.purple.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              '阴影 = 优化区域',
              style: TextStyle(fontSize: 11, color: Colors.purple[700]),
            ),
          ),
        ],
      );
    }
  }

  Widget _buildLegendItem(Color color, String label,
      {bool isDashed = false, bool isSmall = false, bool hasAiTag = false}) {
    return Row(
      mainAxisSize: MainAxisSize.min,
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
            fontWeight: hasAiTag ? FontWeight.bold : FontWeight.normal,
          ),
        ),
        if (hasAiTag) ...[
          const SizedBox(width: 4),
          Icon(
            Icons.psychology,
            size: 14,
            color: Colors.purple[600],
          ),
        ],
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
