part of '../power_chart_widget.dart';

class PowerChartWidget extends StatelessWidget {
  const PowerChartWidget({super.key, required this.chartData});

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
            _PowerChartHeader(titleFontSize: titleFontSize),
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
            if (chartData.isEmpty)
              SizedBox(
                height: chartHeight,
                child: const Center(
                  child: Text(
                    '暂无电网交互时序数据',
                    style: TextStyle(color: Colors.grey),
                  ),
                ),
              )
            else
              SizedBox(
                height: chartHeight,
                child: LineChart(_buildPowerLineChartData(context, chartData)),
              ),
            const SizedBox(height: 16),
            _PowerChartLegend(chartData: chartData),
          ],
        ),
      ),
    );
  }
}

class _PowerChartHeader extends StatelessWidget {
  const _PowerChartHeader({required this.titleFontSize});

  final double titleFontSize;

  @override
  Widget build(BuildContext context) {
    return Row(
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
    );
  }
}
