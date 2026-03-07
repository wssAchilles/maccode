part of '../statistical_panel.dart';

class StatisticalPanel extends StatelessWidget {
  const StatisticalPanel({super.key, required this.statisticalResult});

  final StatisticalResult statisticalResult;

  @override
  Widget build(BuildContext context) {
    if (!statisticalResult.success) {
      return _StatisticalUnavailableCard(
        message: statisticalResult.message ?? '没有数值列或出现错误',
      );
    }

    final suggestions = statisticalResult.suggestions ?? const <String>[];
    final tests =
        statisticalResult.normalityTests ?? const <String, NormalityTest>{};
    final hasContent =
        statisticalResult.summary != null ||
        suggestions.isNotEmpty ||
        tests.isNotEmpty;

    if (!hasContent) {
      return const _StatisticalEmptyState();
    }

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.analytics, size: 28),
                const SizedBox(width: 8),
                Text(
                  '统计检验',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (statisticalResult.summary != null) ...[
              _StatisticalSummarySection(summary: statisticalResult.summary!),
              const SizedBox(height: 16),
            ],
            if (suggestions.isNotEmpty) ...[
              _StatisticalSuggestionsSection(suggestions: suggestions),
              const SizedBox(height: 16),
            ],
            if (tests.isNotEmpty) _StatisticalNormalityTable(tests: tests),
          ],
        ),
      ),
    );
  }
}
