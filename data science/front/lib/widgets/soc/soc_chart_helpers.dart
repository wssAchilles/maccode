part of '../soc_chart_widget.dart';

LineChartData _buildSocLineChartData(
  BuildContext context,
  List<ChartDataPoint> chartData,
) {
  return LineChartData(
    gridData: FlGridData(
      show: true,
      drawVerticalLine: true,
      horizontalInterval: 20,
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
          interval: 20,
          reservedSize: 40,
          getTitlesWidget: (value, meta) {
            return Text(
              '${value.toInt()}%',
              style: const TextStyle(fontSize: 10, color: Colors.grey),
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
    minY: 0,
    maxY: 100,
    lineBarsData: [
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
            var dotColor = Colors.purple;
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
              Colors.purple.withValues(alpha: 0.3),
              Colors.purple.withValues(alpha: 0.1),
            ],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
      ),
    ],
    rangeAnnotations: RangeAnnotations(
      horizontalRangeAnnotations: _buildSocPriceRanges(),
    ),
    lineTouchData: LineTouchData(
      enabled: true,
      touchTooltipData: LineTouchTooltipData(
        getTooltipColor: (LineBarSpot spot) =>
            Colors.purple.withValues(alpha: 0.8),
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
                    style: const TextStyle(color: Colors.white, fontSize: 12),
                  ),
                  TextSpan(
                    text: '${data.priceLabel} (${data.price} 元/kWh)\n',
                    style: TextStyle(
                      color: _getSocPriceColor(data.price),
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

List<HorizontalRangeAnnotation> _buildSocPriceRanges() {
  return [
    HorizontalRangeAnnotation(
      y1: 0,
      y2: 100,
      color: Colors.green.withValues(alpha: 0.05),
    ),
  ];
}

Color _getSocPriceColor(double price) {
  if (price <= 0.3) return Colors.green;
  if (price <= 0.6) return Colors.orange;
  return Colors.red;
}

String _getSocOverallStatus(List<ChartDataPoint> chartData) {
  final chargingHours = chartData.where((data) => data.isCharging).length;
  final dischargingHours = chartData.where((data) => data.isDischarging).length;

  if (chargingHours > dischargingHours) {
    return '📥 充电为主';
  }
  if (dischargingHours > chargingHours) {
    return '📤 放电为主';
  }
  return '⚖️ 平衡模式';
}

Color _getSocOverallStatusColor(List<ChartDataPoint> chartData) {
  final chargingHours = chartData.where((data) => data.isCharging).length;
  final dischargingHours = chartData.where((data) => data.isDischarging).length;

  if (chargingHours > dischargingHours) {
    return Colors.green;
  }
  if (dischargingHours > chargingHours) {
    return Colors.orange;
  }
  return Colors.blue;
}

String _getSocStrategyExplanation(List<ChartDataPoint> chartData) {
  final chargingHours = <int>[];
  final dischargingHours = <int>[];

  for (final data in chartData) {
    if (data.isCharging) {
      chargingHours.add(data.hour);
    } else if (data.isDischarging) {
      dischargingHours.add(data.hour);
    }
  }

  final chargeRange = _formatSocHourRanges(chargingHours);
  final dischargeRange = _formatSocHourRanges(dischargingHours);

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

String _formatSocHourRanges(List<int> hours) {
  if (hours.isEmpty) return '';

  hours.sort();
  if (hours.length == 1) {
    return '${hours.first}:00';
  }

  var isContinuous = true;
  for (var i = 1; i < hours.length; i++) {
    if (hours[i] - hours[i - 1] > 1) {
      isContinuous = false;
      break;
    }
  }

  if (isContinuous) {
    return '${hours.first}:00-${hours.last + 1}:00';
  }
  return '${hours.first}:00-${hours.last + 1}:00';
}
