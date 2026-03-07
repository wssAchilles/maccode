part of '../correlation_matrix_view.dart';

class CorrelationMatrixView extends StatelessWidget {
  const CorrelationMatrixView({
    super.key,
    required this.correlationResult,
    this.isMobile = false,
  });

  final CorrelationResult correlationResult;
  final bool isMobile;

  @override
  Widget build(BuildContext context) {
    if (!correlationResult.success) {
      return _CorrelationUnavailableCard(
        message: correlationResult.message ?? '数据列不足或出现错误',
      );
    }

    final suggestions = correlationResult.suggestions ?? const <String>[];
    final highCorrelations =
        correlationResult.highCorrelations ?? const <HighCorrelation>[];
    final validPairs = _validCorrelationPairs(correlationResult.correlations);
    final hasRawPairs = correlationResult.correlations?.isNotEmpty ?? false;

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.hub, size: 28),
                const SizedBox(width: 8),
                Text(
                  '相关性分析',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (suggestions.isNotEmpty) ...[
              _CorrelationSuggestionsSection(suggestions: suggestions),
              const SizedBox(height: 16),
            ],
            if (highCorrelations.isNotEmpty) ...[
              _HighCorrelationsSection(highCorrelations: highCorrelations),
              const SizedBox(height: 16),
            ],
            if (isMobile)
              _CorrelationMobileView(
                validPairs: validPairs,
                hasRawPairs: hasRawPairs,
              )
            else
              _CorrelationDesktopView(
                validPairs: validPairs,
                hasRawPairs: hasRawPairs,
              ),
          ],
        ),
      ),
    );
  }
}

List<CorrelationPair> _validCorrelationPairs(List<CorrelationPair>? pairs) {
  return (pairs ?? const <CorrelationPair>[])
      .where((pair) => pair.error == null)
      .toList(growable: false);
}
