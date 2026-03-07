part of '../feature_importance_chart.dart';

class _FeatureImportanceCard extends StatelessWidget {
  const _FeatureImportanceCard({
    required this.sortedEntries,
    required this.displayedEntries,
    required this.totalFeatures,
    required this.defaultVisibleCount,
    required this.isExpanded,
    required this.interpretation,
    required this.resolveFeatureName,
    required this.colorForRank,
    required this.onToggleExpanded,
  });

  final List<MapEntry<String, double>> sortedEntries;
  final List<MapEntry<String, double>> displayedEntries;
  final int totalFeatures;
  final int defaultVisibleCount;
  final bool isExpanded;
  final String? interpretation;
  final String Function(String key) resolveFeatureName;
  final Color Function(int rank, int total) colorForRank;
  final VoidCallback? onToggleExpanded;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 420;
        final maxValue = sortedEntries.first.value;

        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 10,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _FeatureImportanceHeader(
                totalFeatures: totalFeatures,
                isCompact: isCompact,
              ),
              const SizedBox(height: 16),
              ConstrainedBox(
                constraints: BoxConstraints(maxHeight: isExpanded ? 500 : 320),
                child: SingleChildScrollView(
                  child: Column(
                    children: displayedEntries.asMap().entries.map((entry) {
                      final index = entry.key;
                      final data = entry.value;
                      final percentage = data.value * 100;
                      final barWidthRatio = maxValue > 0
                          ? (data.value / maxValue).clamp(0.0, 1.0)
                          : 0.0;

                      return _FeatureImportanceBarRow(
                        rank: index + 1,
                        featureName: resolveFeatureName(data.key),
                        percentage: percentage,
                        barWidthRatio: barWidthRatio,
                        color: colorForRank(index, totalFeatures),
                        isCompact: isCompact,
                      );
                    }).toList(),
                  ),
                ),
              ),
              if (onToggleExpanded != null) ...[
                const SizedBox(height: 8),
                Center(
                  child: TextButton.icon(
                    key: const ValueKey('feature-importance-toggle'),
                    onPressed: onToggleExpanded,
                    icon: Icon(
                      isExpanded ? Icons.expand_less : Icons.expand_more,
                      size: 18,
                    ),
                    label: Text(
                      isExpanded
                          ? '收起 (显示前 $defaultVisibleCount 个)'
                          : '展开全部 (${totalFeatures - defaultVisibleCount} 个更多)',
                      style: const TextStyle(fontSize: 12),
                    ),
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 4,
                      ),
                    ),
                  ),
                ),
              ],
              if (interpretation?.trim().isNotEmpty ?? false) ...[
                const SizedBox(height: 12),
                _FeatureInterpretationPanel(text: interpretation!.trim()),
              ],
              const SizedBox(height: 12),
              _TopFeaturesSummary(
                topFeatures: sortedEntries.take(3).toList(),
                resolveFeatureName: resolveFeatureName,
              ),
            ],
          ),
        );
      },
    );
  }
}

class _FeatureImportanceHeader extends StatelessWidget {
  const _FeatureImportanceHeader({
    required this.totalFeatures,
    required this.isCompact,
  });

  final int totalFeatures;
  final bool isCompact;

  @override
  Widget build(BuildContext context) {
    final badge = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        '共 $totalFeatures 个特征',
        style: TextStyle(
          fontSize: 11,
          color: Theme.of(context).colorScheme.onPrimaryContainer,
          fontWeight: FontWeight.w500,
        ),
      ),
    );

    final title = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.insights,
          color: Theme.of(context).colorScheme.primary,
          size: 20,
        ),
        const SizedBox(width: 8),
        Flexible(
          child: Text(
            '特征重要性分析',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
        ),
      ],
    );

    if (isCompact) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [title, const SizedBox(height: 8), badge],
      );
    }

    return Row(
      children: [
        Expanded(child: title),
        const SizedBox(width: 12),
        badge,
      ],
    );
  }
}

class _FeatureImportanceBarRow extends StatelessWidget {
  const _FeatureImportanceBarRow({
    required this.rank,
    required this.featureName,
    required this.percentage,
    required this.barWidthRatio,
    required this.color,
    required this.isCompact,
  });

  final int rank;
  final String featureName;
  final double percentage;
  final double barWidthRatio;
  final Color color;
  final bool isCompact;

  bool get _isTopRank => rank <= 3;

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                SizedBox(
                  width: 24,
                  child: Text(
                    '$rank',
                    style: TextStyle(
                      fontSize: 11,
                      color: _isTopRank
                          ? Theme.of(context).colorScheme.primary
                          : Colors.grey,
                      fontWeight: _isTopRank
                          ? FontWeight.bold
                          : FontWeight.normal,
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    featureName,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  '${percentage.toStringAsFixed(1)}%',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: _isTopRank
                        ? Theme.of(context).colorScheme.primary
                        : Colors.grey[700],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            _FeatureBar(barWidthRatio: barWidthRatio, color: color),
          ],
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 24,
            child: Text(
              '$rank',
              style: TextStyle(
                fontSize: 11,
                color: _isTopRank
                    ? Theme.of(context).colorScheme.primary
                    : Colors.grey,
                fontWeight: _isTopRank ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ),
          SizedBox(
            width: 100,
            child: Text(
              featureName,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _FeatureBar(barWidthRatio: barWidthRatio, color: color),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 56,
            child: Text(
              '${percentage.toStringAsFixed(1)}%',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: _isTopRank
                    ? Theme.of(context).colorScheme.primary
                    : Colors.grey[700],
              ),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}

class _FeatureBar extends StatelessWidget {
  const _FeatureBar({required this.barWidthRatio, required this.color});

  final double barWidthRatio;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Container(
          height: 20,
          decoration: BoxDecoration(
            color: Colors.grey.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        FractionallySizedBox(
          widthFactor: barWidthRatio,
          child: Container(
            height: 20,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [color.withValues(alpha: 0.8), color],
              ),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        ),
      ],
    );
  }
}

class _FeatureInterpretationPanel extends StatelessWidget {
  const _FeatureInterpretationPanel({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(
          context,
        ).colorScheme.primaryContainer.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.lightbulb_outline,
            color: Theme.of(context).colorScheme.primary,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: 13,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TopFeaturesSummary extends StatelessWidget {
  const _TopFeaturesSummary({
    required this.topFeatures,
    required this.resolveFeatureName,
  });

  final List<MapEntry<String, double>> topFeatures;
  final String Function(String key) resolveFeatureName;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.blue.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.star, size: 14, color: Colors.amber[700]),
              const SizedBox(width: 4),
              const Text(
                '最重要的特征',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: topFeatures.asMap().entries.map((entry) {
              final rank = entry.key + 1;
              final feature = entry.value;
              final name = resolveFeatureName(feature.key);
              final color = rank == 1
                  ? Colors.amber[700]!
                  : rank == 2
                  ? Colors.grey[600]!
                  : Colors.brown[400]!;

              return Chip(
                avatar: CircleAvatar(
                  backgroundColor: color,
                  radius: 10,
                  child: Text(
                    '$rank',
                    style: const TextStyle(
                      fontSize: 10,
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                label: Text(
                  '$name (${(feature.value * 100).toStringAsFixed(1)}%)',
                  style: const TextStyle(fontSize: 11),
                ),
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                padding: const EdgeInsets.symmetric(horizontal: 4),
                visualDensity: VisualDensity.compact,
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

class _FeatureImportanceEmptyState extends StatelessWidget {
  const _FeatureImportanceEmptyState();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: const Center(
        child: Text(
          '暂无特征重要性数据',
          key: ValueKey('feature-importance-empty-state'),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}
