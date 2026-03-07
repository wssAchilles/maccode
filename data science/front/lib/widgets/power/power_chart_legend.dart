part of '../power_chart_widget.dart';

class _PowerChartLegend extends StatelessWidget {
  const _PowerChartLegend({required this.chartData});

  final List<ChartDataPoint> chartData;

  @override
  Widget build(BuildContext context) {
    final totalSaving = chartData.fold<double>(
      0,
      (sum, data) => sum + (data.load - data.gridPower).abs(),
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final useCompactLayout =
            ResponsiveHelper.isMobile(context) || constraints.maxWidth < 560;

        if (useCompactLayout) {
          return Column(
            children: [
              Wrap(
                spacing: 12,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: const [
                  _PowerLegendItem(
                    color: Colors.grey,
                    label: 'AI 预测负载',
                    isDashed: true,
                    hasAiTag: true,
                  ),
                  _PowerLegendItem(color: Colors.blue, label: '优化后电网'),
                  _PowerLegendItem(
                    color: Colors.green,
                    label: '充电(填谷)',
                    isSmall: true,
                  ),
                  _PowerLegendItem(
                    color: Colors.orange,
                    label: '放电(削峰)',
                    isSmall: true,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: Colors.green.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  '⚡ 阴影区域 = 削峰填谷效果 (${totalSaving.toStringAsFixed(0)} kWh 优化)',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.green[700],
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          );
        }

        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const _PowerLegendItem(
              color: Colors.grey,
              label: 'AI 预测负载',
              isDashed: true,
              hasAiTag: true,
            ),
            const SizedBox(width: 16),
            const _PowerLegendItem(color: Colors.blue, label: '优化后电网'),
            const SizedBox(width: 16),
            const _PowerLegendItem(
              color: Colors.green,
              label: '充电(填谷)',
              isSmall: true,
            ),
            const SizedBox(width: 8),
            const _PowerLegendItem(
              color: Colors.orange,
              label: '放电(削峰)',
              isSmall: true,
            ),
            const SizedBox(width: 16),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.purple.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '阴影 = 优化区域',
                style: TextStyle(fontSize: 11, color: Colors.purple[700]),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _PowerLegendItem extends StatelessWidget {
  const _PowerLegendItem({
    required this.color,
    required this.label,
    this.isDashed = false,
    this.isSmall = false,
    this.hasAiTag = false,
  });

  final Color color;
  final String label;
  final bool isDashed;
  final bool isSmall;
  final bool hasAiTag;

  @override
  Widget build(BuildContext context) {
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
              ? CustomPaint(painter: _DashedLinePainter(color: color))
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
          Icon(Icons.psychology, size: 14, color: Colors.purple[600]),
        ],
      ],
    );
  }
}

class _DashedLinePainter extends CustomPainter {
  const _DashedLinePainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    const dashWidth = 3.0;
    const dashSpace = 2.0;
    var startX = 0.0;

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
