part of '../soc_chart_widget.dart';

class SocChartWidget extends StatelessWidget {
  const SocChartWidget({super.key, required this.chartData});

  final List<ChartDataPoint> chartData;

  @override
  Widget build(BuildContext context) {
    final chartHeight = ResponsiveHelper.getResponsiveValue(
      context,
      mobile: 250.0,
      tablet: 300.0,
      desktop: 350.0,
    );
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
            _SocChartHeader(titleFontSize: titleFontSize, chartData: chartData),
            const SizedBox(height: 8),
            _SocStrategySummaryCard(chartData: chartData),
            const SizedBox(height: 16),
            if (chartData.isEmpty)
              SizedBox(
                height: chartHeight,
                child: const Center(
                  child: Text(
                    '暂无电池电量时序数据',
                    style: TextStyle(color: Colors.grey),
                  ),
                ),
              )
            else
              SizedBox(
                height: chartHeight,
                child: LineChart(_buildSocLineChartData(context, chartData)),
              ),
            const SizedBox(height: 16),
            _SocChartLegend(context: context),
          ],
        ),
      ),
    );
  }
}

class _SocChartHeader extends StatelessWidget {
  const _SocChartHeader({required this.titleFontSize, required this.chartData});

  final double titleFontSize;
  final List<ChartDataPoint> chartData;

  @override
  Widget build(BuildContext context) {
    final statusColor = _getSocOverallStatusColor(chartData);
    return Row(
      children: [
        Text(
          '🔋 电池电量变化',
          style: TextStyle(
            fontSize: titleFontSize,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: statusColor.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            _getSocOverallStatus(chartData),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: statusColor,
            ),
          ),
        ),
      ],
    );
  }
}

class _SocStrategySummaryCard extends StatelessWidget {
  const _SocStrategySummaryCard({required this.chartData});

  final List<ChartDataPoint> chartData;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.purple.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.purple.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(Icons.lightbulb_outline, size: 16, color: Colors.purple[600]),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _getSocStrategyExplanation(chartData),
              style: TextStyle(fontSize: 12, color: Colors.grey[700]),
            ),
          ),
        ],
      ),
    );
  }
}
