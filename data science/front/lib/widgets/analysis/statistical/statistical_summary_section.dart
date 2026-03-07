part of '../statistical_panel.dart';

class _StatisticalSummarySection extends StatelessWidget {
  const _StatisticalSummarySection({required this.summary});

  final TestSummary summary;

  @override
  Widget build(BuildContext context) {
    final items = [
      _StatisticalSummaryItemData(
        icon: Icons.functions,
        label: '总列数',
        value: summary.totalNumericColumns.toString(),
        color: Colors.blue,
      ),
      _StatisticalSummaryItemData(
        icon: Icons.check_circle,
        label: '正态分布',
        value: summary.normalDistributionCount.toString(),
        color: Colors.green,
      ),
      _StatisticalSummaryItemData(
        icon: Icons.warning,
        label: '非正态',
        value: summary.nonNormalDistributionCount.toString(),
        color: Colors.orange,
      ),
    ];

    return Container(
      key: const ValueKey('statistical-summary-section'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 420) {
            return Column(
              children: [
                for (var index = 0; index < items.length; index++)
                  Padding(
                    padding: EdgeInsets.only(
                      bottom: index < items.length - 1 ? 12 : 0,
                    ),
                    child: _StatisticalSummaryItem(item: items[index]),
                  ),
              ],
            );
          }

          return Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              for (var index = 0; index < items.length; index++) ...[
                _StatisticalSummaryItem(item: items[index]),
                if (index < items.length - 1)
                  Container(width: 1, height: 40, color: Colors.grey.shade300),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _StatisticalSummaryItemData {
  const _StatisticalSummaryItemData({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;
}

class _StatisticalSummaryItem extends StatelessWidget {
  const _StatisticalSummaryItem({required this.item});

  final _StatisticalSummaryItemData item;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(item.icon, color: item.color, size: 24),
        const SizedBox(height: 4),
        Text(
          item.value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: item.color,
          ),
        ),
        Text(
          item.label,
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
      ],
    );
  }
}
