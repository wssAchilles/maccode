part of '../optimization_insights_section.dart';

class OptimizationStrategyDetailsCard extends StatelessWidget {
  const OptimizationStrategyDetailsCard({
    super.key,
    required this.optimization,
  });

  final OptimizationData optimization;

  @override
  Widget build(BuildContext context) {
    final strategy = optimization.strategy;
    final summary = optimization.summary;

    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.schedule, color: Colors.blue[700], size: 24),
                const SizedBox(width: 8),
                const Text(
                  '⚡ 充放电策略',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _StrategyWindowCard(
              icon: Icons.battery_charging_full,
              iconColor: Colors.green,
              label: '充电时段',
              value: strategy.chargingHoursFormatted,
              count: '${strategy.chargingCount} 小时',
              backgroundColor: Colors.green[50]!,
            ),
            const SizedBox(height: 12),
            _StrategyWindowCard(
              icon: Icons.flash_on,
              iconColor: Colors.red,
              label: '放电时段',
              value: strategy.dischargingHoursFormatted,
              count: '${strategy.dischargingCount} 小时',
              backgroundColor: Colors.red[50]!,
            ),
            const SizedBox(height: 16),
            _StrategySummaryCard(summary: summary),
          ],
        ),
      ),
    );
  }
}

class _StrategyWindowCard extends StatelessWidget {
  const _StrategyWindowCard({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    required this.count,
    required this.backgroundColor,
  });

  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final String count;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: iconColor, size: 20),
              const SizedBox(width: 8),
              Text(
                label,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: iconColor.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  count,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: iconColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(value, style: TextStyle(fontSize: 13, color: Colors.grey[700])),
        ],
      ),
    );
  }
}

class _StrategySummaryCard extends StatelessWidget {
  const _StrategySummaryCard({required this.summary});

  final OptimizationSummary summary;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue[50],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          _StrategySummaryRow(
            label: '总充电量',
            value: '${summary.totalCharged.toStringAsFixed(2)} kWh',
          ),
          const Divider(height: 16),
          _StrategySummaryRow(
            label: '总放电量',
            value: '${summary.totalDischarged.toStringAsFixed(2)} kWh',
          ),
          const Divider(height: 16),
          _StrategySummaryRow(
            label: '循环效率',
            value: '${summary.cycleEfficiency.toStringAsFixed(1)}%',
          ),
        ],
      ),
    );
  }
}

class _StrategySummaryRow extends StatelessWidget {
  const _StrategySummaryRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 14)),
        Text(
          value,
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}
