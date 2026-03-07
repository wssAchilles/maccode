part of '../soc_chart_widget.dart';

class _SocChartLegend extends StatelessWidget {
  const _SocChartLegend({required this.context});

  final BuildContext context;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: ResponsiveHelper.getResponsiveValue(
        this.context,
        mobile: 12.0,
        tablet: 16.0,
      ),
      runSpacing: 8,
      alignment: WrapAlignment.center,
      children: const [
        _SocLegendItem(color: Colors.purple, label: 'SOC 趋势'),
        _SocLegendItem(
          color: Color.fromRGBO(76, 175, 80, 0.3),
          label: '谷时 (0.3元)',
          isBackground: true,
        ),
        _SocLegendItem(
          color: Color.fromRGBO(255, 152, 0, 0.3),
          label: '平时 (0.6元)',
          isBackground: true,
        ),
        _SocLegendItem(
          color: Color.fromRGBO(244, 67, 54, 0.3),
          label: '峰时 (1.0元)',
          isBackground: true,
        ),
      ],
    );
  }
}

class _SocLegendItem extends StatelessWidget {
  const _SocLegendItem({
    required this.color,
    required this.label,
    this.isBackground = false,
  });

  final Color color;
  final String label;
  final bool isBackground;

  @override
  Widget build(BuildContext context) {
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
        Text(label, style: TextStyle(fontSize: 11, color: Colors.grey[700])),
      ],
    );
  }
}
