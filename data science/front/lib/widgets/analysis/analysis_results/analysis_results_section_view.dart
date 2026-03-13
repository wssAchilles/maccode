part of '../analysis_results_section.dart';

class AnalysisResultsSection extends StatelessWidget {
  const AnalysisResultsSection({
    super.key,
    required this.result,
    this.chain,
    this.continuationContext,
  });

  final AnalysisResult result;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  List<String> _previewColumns() {
    final orderedColumns = <String>[];
    final seen = <String>{};

    for (final column in result.basicInfo.columnNames) {
      if (seen.add(column)) {
        orderedColumns.add(column);
      }
    }

    for (final row in result.preview) {
      for (final key in row.keys) {
        final column = key.toString();
        if (seen.add(column)) {
          orderedColumns.add(column);
        }
      }
    }

    return orderedColumns;
  }

  @override
  Widget build(BuildContext context) {
    final previewColumns = _previewColumns();

    return LayoutBuilder(
      builder: (context, constraints) {
        final isMobile = constraints.maxWidth < 800;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _ResultSummaryBanner(
              result: result,
              chain: chain,
              continuationContext: continuationContext,
            ),
            const SizedBox(height: 16),
            _AssetConsoleSection(
              result: result,
              chain: chain,
              continuationContext: continuationContext,
            ),
            const SizedBox(height: 16),
            AssetChainSectionHeader(
              title: '详细分析面板',
              subtitle: '把质量、统计检验和相关性放到同一诊断面板里，便于按当前链路焦点继续深入。',
              chain: chain,
              continuationContext: continuationContext,
              icon: Icons.analytics_rounded,
            ),
            const SizedBox(height: 12),
            if (isMobile) ...[
              if (result.qualityAnalysis != null)
                QualityDashboard(qualityAnalysis: result.qualityAnalysis!),
              const SizedBox(height: 16),
              _BasicInfoCard(result: result),
              if (result.statisticalTests != null) ...[
                const SizedBox(height: 16),
                StatisticalPanel(statisticalResult: result.statisticalTests!),
              ],
              if (result.correlations != null) ...[
                const SizedBox(height: 16),
                CorrelationMatrixView(
                  correlationResult: result.correlations!,
                  isMobile: true,
                ),
              ],
            ] else
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 3,
                    child: Column(
                      children: [
                        if (result.qualityAnalysis != null)
                          QualityDashboard(
                            qualityAnalysis: result.qualityAnalysis!,
                          ),
                        const SizedBox(height: 16),
                        _BasicInfoCard(result: result),
                      ],
                    ),
                  ),
                  const SizedBox(width: 24),
                  Expanded(
                    flex: 7,
                    child: Column(
                      children: [
                        if (result.statisticalTests != null)
                          StatisticalPanel(
                            statisticalResult: result.statisticalTests!,
                          ),
                        if (result.correlations != null) ...[
                          const SizedBox(height: 16),
                          CorrelationMatrixView(
                            correlationResult: result.correlations!,
                            isMobile: false,
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            if (previewColumns.isNotEmpty && result.preview.isNotEmpty) ...[
              const SizedBox(height: 16),
              _PreviewCard(preview: result.preview, columns: previewColumns),
            ],
          ],
        );
      },
    );
  }
}
