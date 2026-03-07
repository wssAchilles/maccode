part of '../power_chart_widget.dart';

LineChartData _buildPowerLineChartData(
  BuildContext context,
  List<ChartDataPoint> chartData,
) {
  return LineChartData(
    gridData: FlGridData(
      show: true,
      drawVerticalLine: true,
      horizontalInterval: 50,
      verticalInterval: 4,
      getDrawingHorizontalLine: (value) {
        return FlLine(
          color: Colors.grey.withValues(alpha: 0.2),
          strokeWidth: 1,
        );
      },
      getDrawingVerticalLine: (value) {
        return FlLine(
          color: Colors.grey.withValues(alpha: 0.2),
          strokeWidth: 1,
        );
      },
    ),
    titlesData: FlTitlesData(
      show: true,
      rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
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
                style: const TextStyle(fontSize: 10, color: Colors.grey),
              );
            }
            return const Text('');
          },
        ),
      ),
      leftTitles: AxisTitles(
        sideTitles: SideTitles(
          showTitles: true,
          interval: _getPowerYAxisInterval(chartData),
          reservedSize: 65,
          getTitlesWidget: (value, meta) {
            final label = value.abs() >= 1000
                ? '${(value / 1000).toStringAsFixed(1)}k'
                : value.toInt().toString();
            return Padding(
              padding: const EdgeInsets.only(right: 4),
              child: Text(
                label,
                style: const TextStyle(fontSize: 10, color: Colors.grey),
                textAlign: TextAlign.right,
              ),
            );
          },
        ),
      ),
    ),
    borderData: FlBorderData(
      show: true,
      border: Border.all(color: Colors.grey.withValues(alpha: 0.3)),
    ),
    minX: 0,
    maxX: 23,
    minY: _getPowerMinY(chartData),
    maxY: _getPowerMaxY(chartData),
    lineBarsData: [
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
        dashArray: const [5, 5],
      ),
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
            var dotColor = Colors.blue;
            if (data.isCharging) {
              dotColor = Colors.green;
            } else if (data.isDischarging) {
              dotColor = Colors.orange;
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
              Colors.blue.withValues(alpha: 0.2),
              Colors.blue.withValues(alpha: 0.05),
            ],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
      ),
    ],
    betweenBarsData: [
      BetweenBarsData(
        fromIndex: 0,
        toIndex: 1,
        color: _getPowerDifferenceColor(chartData),
      ),
    ],
    extraLinesData: ExtraLinesData(
      horizontalLines: [
        HorizontalLine(
          y: 0,
          color: Colors.black.withValues(alpha: 0.3),
          strokeWidth: 1,
          dashArray: const [5, 5],
        ),
      ],
    ),
    lineTouchData: LineTouchData(
      enabled: true,
      touchTooltipData: LineTouchTooltipData(
        getTooltipColor: (LineBarSpot spot) =>
            Colors.blueGrey.withValues(alpha: 0.8),
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
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
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

double _getPowerMinY(List<ChartDataPoint> chartData) {
  if (chartData.isEmpty) {
    return 0;
  }

  final minLoad = chartData.map((e) => e.load).reduce((a, b) => a < b ? a : b);
  final minGrid = chartData
      .map((e) => e.gridPower)
      .reduce((a, b) => a < b ? a : b);
  return (minLoad < minGrid ? minLoad : minGrid) * 0.9;
}

double _getPowerMaxY(List<ChartDataPoint> chartData) {
  if (chartData.isEmpty) {
    return 100;
  }

  final maxLoad = chartData.map((e) => e.load).reduce((a, b) => a > b ? a : b);
  final maxGrid = chartData
      .map((e) => e.gridPower)
      .reduce((a, b) => a > b ? a : b);
  return (maxLoad > maxGrid ? maxLoad : maxGrid) * 1.1;
}

double _getPowerYAxisInterval(List<ChartDataPoint> chartData) {
  final range = _getPowerMaxY(chartData) - _getPowerMinY(chartData);
  if (range > 10000) return 5000;
  if (range > 5000) return 2000;
  if (range > 1000) return 500;
  if (range > 500) return 100;
  return 50;
}

Color _getPowerDifferenceColor(List<ChartDataPoint> chartData) {
  if (chartData.isEmpty) {
    return Colors.blue.withValues(alpha: 0.1);
  }

  var totalCharging = 0.0;
  var totalDischarging = 0.0;

  for (final data in chartData) {
    if (data.isCharging) {
      totalCharging += data.chargePower;
    } else if (data.isDischarging) {
      totalDischarging += data.dischargePower;
    }
  }

  if (totalCharging > totalDischarging) {
    return Colors.green.withValues(alpha: 0.15);
  }
  return Colors.orange.withValues(alpha: 0.15);
}
