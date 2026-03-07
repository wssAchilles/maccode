part of '../correlation_matrix_view.dart';

class _CorrelationUnavailableCard extends StatelessWidget {
  const _CorrelationUnavailableCard({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.orange),
            const SizedBox(height: 8),
            Text('相关性分析不可用', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              message,
              style: const TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _CorrelationSuggestionsSection extends StatelessWidget {
  const _CorrelationSuggestionsSection({required this.suggestions});

  final List<String> suggestions;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blue.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline, color: Colors.blue.shade700),
              const SizedBox(width: 8),
              Text(
                '分析建议',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Colors.blue.shade700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...suggestions.map(
            (suggestion) => Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('• ', style: TextStyle(fontSize: 16)),
                  Expanded(
                    child: Text(
                      suggestion,
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HighCorrelationsSection extends StatelessWidget {
  const _HighCorrelationsSection({required this.highCorrelations});

  final List<HighCorrelation> highCorrelations;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.orange.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.orange.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber, color: Colors.orange.shade700),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '高相关性变量 (|r| > 0.7)',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.orange.shade700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...highCorrelations.map(
            (highCorrelation) =>
                _HighCorrelationRow(highCorrelation: highCorrelation),
          ),
        ],
      ),
    );
  }
}

class _HighCorrelationRow extends StatelessWidget {
  const _HighCorrelationRow({required this.highCorrelation});

  final HighCorrelation highCorrelation;

  @override
  Widget build(BuildContext context) {
    final color = _getCorrelationColor(highCorrelation.correlation);
    final badge = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color),
      ),
      child: Text(
        'r = ${highCorrelation.correlation.toStringAsFixed(3)}',
        style: TextStyle(
          fontWeight: FontWeight.bold,
          fontSize: 13,
          color: color,
        ),
      ),
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final label = _formatHighCorrelationLabel(highCorrelation);
          if (constraints.maxWidth < 420) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontWeight: FontWeight.w500,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 8),
                badge,
              ],
            );
          }

          return Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontWeight: FontWeight.w500,
                    fontSize: 14,
                  ),
                ),
              ),
              badge,
            ],
          );
        },
      ),
    );
  }
}

String _formatHighCorrelationLabel(HighCorrelation highCorrelation) {
  final variables = highCorrelation.variables;
  if (variables.length >= 2) {
    return '${variables[0]} ↔️ ${variables[1]}';
  }
  if (variables.length == 1) {
    return '${variables[0]} ↔️ 未知变量';
  }
  return '变量对缺失';
}

String _formatPValue(double pValue) {
  return pValue < 0.001 ? '<0.001' : pValue.toStringAsFixed(3);
}

Color _getCorrelationColor(double correlation) {
  final absCorrelation = correlation.abs();
  if (absCorrelation >= 0.7) {
    return Colors.red;
  }
  if (absCorrelation >= 0.4) {
    return Colors.orange;
  }
  return Colors.blue;
}
