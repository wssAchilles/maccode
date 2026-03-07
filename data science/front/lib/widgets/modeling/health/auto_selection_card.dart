part of '../modeling_health_section.dart';

class _AutoSelectionCard extends StatelessWidget {
  const _AutoSelectionCard({required this.modelInfo});

  final ModelInfo modelInfo;

  @override
  Widget build(BuildContext context) {
    final autoSelection = modelInfo.autoSelection!;
    return Container(
      key: const ValueKey('modeling-auto-selection-card'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.green[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.green[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome, color: Colors.green[700], size: 18),
              const SizedBox(width: 8),
              Text(
                '🤖 自动模型选择',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.green[900],
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.green[600],
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Text(
                  '已启用',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _AutoSelectionMetricRow(
            first: _AutoSelectionItem(
              label: '🏆 胜出模型',
              value: autoSelection.winner,
              color: Colors.amber[700]!,
            ),
            second: _AutoSelectionItem(
              label: '📈 性能提升',
              value: autoSelection.improvementOverBaseline,
              color: Colors.green[700]!,
            ),
          ),
          const SizedBox(height: 8),
          _AutoSelectionMetricRow(
            first: _AutoSelectionItem(
              label: '🔬 验证方法',
              value: autoSelection.validationMethodFormatted,
              color: Colors.blue[700]!,
            ),
            second: _AutoSelectionItem(
              label: '📊 候选模型',
              value: '${autoSelection.candidatesEvaluated.length} 个',
              color: Colors.purple[700]!,
            ),
          ),
          if (autoSelection.allScores != null &&
              autoSelection.allScores!.isNotEmpty) ...[
            const SizedBox(height: 12),
            ExpansionTile(
              key: const ValueKey('modeling-auto-selection-scores-toggle'),
              tilePadding: EdgeInsets.zero,
              childrenPadding: EdgeInsets.zero,
              title: Text(
                '查看所有候选模型得分',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.green[700],
                  fontWeight: FontWeight.w500,
                ),
              ),
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Column(
                    children: autoSelection.allScores!.entries.map((entry) {
                      final scores = switch (entry.value) {
                        final Map<dynamic, dynamic> map =>
                          map.cast<String, dynamic>(),
                        _ => const <String, dynamic>{},
                      };
                      final isWinner = entry.key == autoSelection.winner;
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          children: [
                            if (isWinner)
                              const Text('🏆 ', style: TextStyle(fontSize: 12))
                            else
                              const SizedBox(width: 18),
                            Expanded(
                              child: Text(
                                entry.key,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: isWinner
                                      ? FontWeight.bold
                                      : FontWeight.normal,
                                  color: isWinner
                                      ? Colors.amber[800]
                                      : Colors.grey[700],
                                ),
                              ),
                            ),
                            Text(
                              _formatAutoSelectionScore(scores['mae']),
                              style: TextStyle(
                                fontSize: 11,
                                color: isWinner
                                    ? Colors.green[700]
                                    : Colors.grey[600],
                                fontWeight: isWinner
                                    ? FontWeight.bold
                                    : FontWeight.normal,
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _AutoSelectionMetricRow extends StatelessWidget {
  const _AutoSelectionMetricRow({required this.first, required this.second});

  final Widget first;
  final Widget second;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 420) {
          return Column(children: [first, const SizedBox(height: 8), second]);
        }

        return Row(
          children: [
            Expanded(child: first),
            const SizedBox(width: 8),
            Expanded(child: second),
          ],
        );
      },
    );
  }
}

class _AutoSelectionItem extends StatelessWidget {
  const _AutoSelectionItem({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontSize: 10, color: Colors.grey[600])),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

String _formatAutoSelectionScore(Object? rawValue) {
  final value = switch (rawValue) {
    final num number => number.toDouble(),
    final String text => double.tryParse(text),
    _ => null,
  };

  if (value == null) {
    return 'MAE: N/A';
  }

  return 'MAE: ${value.toStringAsFixed(2)} kW';
}
