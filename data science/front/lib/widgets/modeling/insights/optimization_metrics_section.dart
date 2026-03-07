part of '../optimization_insights_section.dart';

class OptimizationMetricsSection extends StatelessWidget {
  const OptimizationMetricsSection({
    super.key,
    required this.optimization,
    this.previousResult,
  });

  final OptimizationData optimization;
  final OptimizationResponse? previousResult;

  @override
  Widget build(BuildContext context) {
    final summary = optimization.summary;
    final previousOptimization = previousResult?.optimization;
    final savingsDiff = previousOptimization == null
        ? null
        : summary.savings - previousOptimization.summary.savings;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _OptimizationMetricsHeader(savingsDiff: savingsDiff),
        const SizedBox(height: 12),
        _OptimizationSavingsCards(summary: summary),
        const SizedBox(height: 12),
        _CostComparisonCard(summary: summary),
      ],
    );
  }
}

class _OptimizationMetricsHeader extends StatelessWidget {
  const _OptimizationMetricsHeader({required this.savingsDiff});

  final double? savingsDiff;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(Icons.analytics, color: Colors.blue[700], size: 24),
        const SizedBox(width: 8),
        const Text(
          '💰 优化效果',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const Spacer(),
        if (savingsDiff != null && savingsDiff!.abs() > 0.01)
          _SavingsDiffBadge(savingsDiff: savingsDiff!),
      ],
    );
  }
}

class _SavingsDiffBadge extends StatelessWidget {
  const _SavingsDiffBadge({required this.savingsDiff});

  final double savingsDiff;

  @override
  Widget build(BuildContext context) {
    final isPositive = savingsDiff > 0;
    final badgeColor = isPositive ? Colors.green : Colors.red;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: badgeColor.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isPositive ? Icons.trending_up : Icons.trending_down,
            size: 14,
            color: badgeColor[700],
          ),
          const SizedBox(width: 4),
          Text(
            '${isPositive ? "+" : ""}${savingsDiff.toStringAsFixed(2)}元 vs 上次',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: badgeColor[700],
            ),
          ),
        ],
      ),
    );
  }
}

class _OptimizationSavingsCards extends StatelessWidget {
  const _OptimizationSavingsCards({required this.summary});

  final OptimizationSummary summary;

  @override
  Widget build(BuildContext context) {
    final savingsCard = _MetricCard(
      icon: Icons.savings,
      iconColor: Colors.green,
      label: '节省金额',
      value: summary.savingsFormatted,
      backgroundColor: Colors.green[50]!,
      valueColor: Colors.green[700]!,
    );
    final percentageCard = _MetricCard(
      icon: Icons.percent,
      iconColor: Colors.orange,
      label: '节省比例',
      value: summary.savingsPercentFormatted,
      backgroundColor: Colors.orange[50]!,
      valueColor: Colors.orange[700]!,
    );

    if (ResponsiveHelper.isMobile(context)) {
      return Column(
        children: [savingsCard, const SizedBox(height: 12), percentageCard],
      );
    }

    return Row(
      children: [
        Expanded(child: savingsCard),
        const SizedBox(width: 12),
        Expanded(child: percentageCard),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    required this.backgroundColor,
    required this.valueColor,
  });

  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final Color backgroundColor;
  final Color valueColor;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      color: backgroundColor,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: iconColor, size: 32),
            const SizedBox(height: 12),
            Text(
              label,
              style: TextStyle(fontSize: 14, color: Colors.grey[700]),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: valueColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CostComparisonCard extends StatelessWidget {
  const _CostComparisonCard({required this.summary});

  final OptimizationSummary summary;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.compare_arrows, color: Colors.blue[700]),
                const SizedBox(width: 8),
                const Text(
                  '成本对比',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _CostComparisonRow(
              label: '无电池成本',
              cost: summary.totalCostWithoutBattery,
              color: Colors.grey,
            ),
            const SizedBox(height: 8),
            _CostComparisonRow(
              label: '有电池成本',
              cost: summary.totalCostWithBattery,
              color: Colors.blue,
            ),
            const Divider(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  '总计节省',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                Text(
                  summary.savingsFormatted,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Colors.green[700],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _CostComparisonRow extends StatelessWidget {
  const _CostComparisonRow({
    required this.label,
    required this.cost,
    required this.color,
  });

  final String label;
  final double cost;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(
          children: [
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 8),
            Text(label, style: const TextStyle(fontSize: 14)),
          ],
        ),
        Text(
          '¥${cost.toStringAsFixed(2)}',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }
}
