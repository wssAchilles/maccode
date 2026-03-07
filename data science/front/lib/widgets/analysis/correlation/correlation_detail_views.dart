part of '../correlation_matrix_view.dart';

class _CorrelationMobileView extends StatelessWidget {
  const _CorrelationMobileView({
    required this.validPairs,
    required this.hasRawPairs,
  });

  final List<CorrelationPair> validPairs;
  final bool hasRawPairs;

  @override
  Widget build(BuildContext context) {
    if (validPairs.isEmpty) {
      return _CorrelationEmptyState(hasRawPairs: hasRawPairs);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '相关系数详情',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        ...validPairs.map((pair) => _CorrelationCard(pair: pair)),
      ],
    );
  }
}

class _CorrelationDesktopView extends StatelessWidget {
  const _CorrelationDesktopView({
    required this.validPairs,
    required this.hasRawPairs,
  });

  final List<CorrelationPair> validPairs;
  final bool hasRawPairs;

  @override
  Widget build(BuildContext context) {
    if (validPairs.isEmpty) {
      return _CorrelationEmptyState(hasRawPairs: hasRawPairs);
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        headingRowColor: WidgetStatePropertyAll(Colors.grey.shade100),
        columns: const [
          DataColumn(
            label: Text('变量 X', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
          DataColumn(
            label: Text('变量 Y', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
          DataColumn(
            label: Text(
              'Pearson r',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          DataColumn(
            label: Text(
              'p-value',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          DataColumn(
            label: Text(
              'Spearman ρ',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          DataColumn(
            label: Text('样本数', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
        ],
        rows: validPairs
            .map(
              (pair) => DataRow(
                cells: [
                  DataCell(Text(pair.variableX)),
                  DataCell(Text(pair.variableY)),
                  DataCell(
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: _getCorrelationColor(
                          pair.pearson.correlation,
                        ).withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        pair.pearson.correlation.toStringAsFixed(3),
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: _getCorrelationColor(pair.pearson.correlation),
                        ),
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      _formatPValue(pair.pearson.pValue),
                      style: TextStyle(
                        color: pair.pearson.significant
                            ? Colors.green
                            : Colors.grey,
                        fontWeight: pair.pearson.significant
                            ? FontWeight.bold
                            : FontWeight.normal,
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      pair.spearman.correlation.toStringAsFixed(3),
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                  ),
                  DataCell(Text(pair.nSamples.toString())),
                ],
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _CorrelationCard extends StatelessWidget {
  const _CorrelationCard({required this.pair});

  final CorrelationPair pair;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${pair.variableX} ↔️ ${pair.variableY}',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                ),
                if (pair.pearson.significant)
                  const Icon(Icons.check_circle, color: Colors.green, size: 20),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _CorrelationCoefficientPill(
                    label: 'Pearson',
                    correlation: pair.pearson.correlation,
                    pValue: pair.pearson.pValue,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _CorrelationCoefficientPill(
                    label: 'Spearman',
                    correlation: pair.spearman.correlation,
                    pValue: pair.spearman.pValue,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '样本数: ${pair.nSamples}',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}

class _CorrelationCoefficientPill extends StatelessWidget {
  const _CorrelationCoefficientPill({
    required this.label,
    required this.correlation,
    required this.pValue,
  });

  final String label;
  final double correlation;
  final double pValue;

  @override
  Widget build(BuildContext context) {
    final color = _getCorrelationColor(correlation);
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            'r = ${correlation.toStringAsFixed(3)}',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            'p ${pValue < 0.001 ? '<0.001' : '=${pValue.toStringAsFixed(3)}'}',
            style: const TextStyle(fontSize: 11, color: Colors.grey),
          ),
        ],
      ),
    );
  }
}

class _CorrelationEmptyState extends StatelessWidget {
  const _CorrelationEmptyState({required this.hasRawPairs});

  final bool hasRawPairs;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        hasRawPairs ? '相关性详情暂不可展示' : '没有足够的数值列进行相关性分析',
        key: const ValueKey('correlation-empty-state'),
        textAlign: TextAlign.center,
      ),
    );
  }
}
