part of '../quality_dashboard.dart';

class _QualityErrorState extends StatelessWidget {
  const _QualityErrorState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 8),
            Text('质量检查失败', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              message,
              style: const TextStyle(color: Colors.red),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _QualityDashboardHeader extends StatelessWidget {
  const _QualityDashboardHeader({required this.isCompact});

  final bool isCompact;

  @override
  Widget build(BuildContext context) {
    final title = Text(
      '数据质量评估',
      style: Theme.of(
        context,
      ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
      textAlign: TextAlign.center,
    );

    if (isCompact) {
      return Column(
        children: [
          const Icon(Icons.assessment, size: 28),
          const SizedBox(height: 8),
          title,
        ],
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(Icons.assessment, size: 28),
        const SizedBox(width: 8),
        Flexible(child: title),
      ],
    );
  }
}

class _QualityScoreSection extends StatelessWidget {
  const _QualityScoreSection({
    required this.score,
    required this.scoreColor,
    required this.scoreLabel,
    required this.isCompact,
  });

  final double score;
  final Color scoreColor;
  final String scoreLabel;
  final bool isCompact;

  @override
  Widget build(BuildContext context) {
    final radius = isCompact ? 64.0 : 80.0;
    final lineWidth = isCompact ? 12.0 : 16.0;

    return Column(
      children: [
        CircularPercentIndicator(
          radius: radius,
          lineWidth: lineWidth,
          percent: score / 100,
          center: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                score.toStringAsFixed(1),
                key: const ValueKey('quality-dashboard-score'),
                style: TextStyle(
                  fontSize: isCompact ? 26 : 32,
                  fontWeight: FontWeight.bold,
                  color: scoreColor,
                ),
              ),
              const Text(
                '/ 100',
                style: TextStyle(fontSize: 16, color: Colors.grey),
              ),
            ],
          ),
          progressColor: scoreColor,
          backgroundColor: Colors.grey.shade300,
          circularStrokeCap: CircularStrokeCap.round,
          animation: true,
          animationDuration: 1200,
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: scoreColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: scoreColor, width: 2),
          ),
          child: Text(
            scoreLabel,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: scoreColor,
            ),
          ),
        ),
      ],
    );
  }
}

class _QualityMetricsSummary extends StatelessWidget {
  const _QualityMetricsSummary({required this.metrics});

  final QualityMetrics metrics;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          _MetricRow(
            icon: Icons.grid_on,
            label: '总单元格',
            value: metrics.totalCells.toString(),
            color: Colors.blue,
          ),
          const SizedBox(height: 8),
          _MetricRow(
            icon: Icons.block,
            label: '缺失值',
            value:
                '${metrics.totalMissing} (${metrics.missingRate.toStringAsFixed(1)}%)',
            color: metrics.missingRate > 5 ? Colors.red : Colors.green,
          ),
          const SizedBox(height: 8),
          _MetricRow(
            icon: Icons.warning_amber,
            label: '异常值',
            value: metrics.totalOutliers.toString(),
            color: metrics.totalOutliers > 0 ? Colors.orange : Colors.green,
          ),
          const SizedBox(height: 8),
          _MetricRow(
            icon: Icons.copy,
            label: '重复行',
            value: metrics.duplicateRows.toString(),
            color: metrics.duplicateRows > 0 ? Colors.orange : Colors.green,
          ),
        ],
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: color),
        const SizedBox(width: 8),
        Expanded(child: Text(label, style: const TextStyle(fontSize: 14))),
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }
}

class _HighRiskWarning extends StatelessWidget {
  const _HighRiskWarning({required this.highRiskColumns});

  final List<String> highRiskColumns;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning, color: Colors.red.shade700),
              const SizedBox(width: 8),
              Text(
                '高风险列 (缺失率>5%)',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.red.shade700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: highRiskColumns
                .map(
                  (col) => Chip(
                    avatar: Icon(
                      Icons.error_outline,
                      size: 16,
                      color: Colors.red.shade700,
                    ),
                    label: Text(col),
                    backgroundColor: Colors.red.shade100,
                    side: BorderSide(color: Colors.red.shade300),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _RecommendationsSection extends StatelessWidget {
  const _RecommendationsSection({required this.recommendations});

  final List<String> recommendations;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.lightbulb_outline, color: Colors.amber),
            const SizedBox(width: 8),
            Text(
              '改进建议',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ...recommendations.asMap().entries.map((entry) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  margin: const EdgeInsets.only(top: 4),
                  padding: const EdgeInsets.all(4),
                  decoration: const BoxDecoration(
                    color: Colors.amber,
                    shape: BoxShape.circle,
                  ),
                  child: Text(
                    '${entry.key + 1}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    entry.value,
                    style: const TextStyle(fontSize: 14, height: 1.5),
                  ),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }
}

class _QualityEmptyDetails extends StatelessWidget {
  const _QualityEmptyDetails();

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const ValueKey('quality-dashboard-empty-details'),
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: const Row(
        children: [
          Icon(Icons.info_outline, size: 18, color: Colors.grey),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              '暂无详细质量指标',
              style: TextStyle(fontSize: 13, color: Colors.black54),
            ),
          ),
        ],
      ),
    );
  }
}
