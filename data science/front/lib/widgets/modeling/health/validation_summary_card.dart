part of '../modeling_health_section.dart';

class _ValidationSummaryCard extends StatelessWidget {
  const _ValidationSummaryCard({required this.modelInfo});

  final ModelInfo modelInfo;

  @override
  Widget build(BuildContext context) {
    final validation = modelInfo.validationSummary;
    final coverage = modelInfo.dataCoverage;

    return Container(
      key: const ValueKey('modeling-validation-summary-card'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.indigo[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.indigo[100]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.verified, color: Colors.indigo[700], size: 18),
              const SizedBox(width: 8),
              const Text(
                '验证与数据覆盖',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (validation != null) ...[
            _ValidationSummaryStatRow(
              first: ModelingStatItem(
                icon: Icons.rule,
                label: '验证方式',
                value: validation.method ?? 'N/A',
                color: Colors.indigo[800]!,
              ),
              second: ModelingStatItem(
                icon: Icons.repeat,
                label: '折数',
                value: validation.cvFolds?.toString() ?? '—',
                color: Colors.deepPurple[700]!,
              ),
            ),
            const SizedBox(height: 10),
            _ValidationSummaryStatRow(
              first: ModelingStatItem(
                icon: Icons.assessment,
                label: 'CV MAE',
                value: validation.cvMaeMean != null
                    ? '${validation.cvMaeMean!.toStringAsFixed(2)} kW ± '
                          '${validation.cvMaeStd?.toStringAsFixed(2) ?? "0"}'
                    : 'N/A',
                color: Colors.teal[700]!,
              ),
              second: ModelingStatItem(
                icon: Icons.check_circle,
                label: 'Holdout MAE',
                value: validation.holdoutMae != null
                    ? '${validation.holdoutMae!.toStringAsFixed(2)} kW'
                    : 'N/A',
                color: Colors.blueGrey[700]!,
              ),
            ),
            const SizedBox(height: 10),
          ],
          if (coverage != null) _DataCoverageCard(coverage: coverage),
        ],
      ),
    );
  }
}

class _ValidationSummaryStatRow extends StatelessWidget {
  const _ValidationSummaryStatRow({required this.first, required this.second});

  final Widget first;
  final Widget second;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 460) {
          return Column(children: [first, const SizedBox(height: 12), second]);
        }

        return Row(
          children: [
            Expanded(child: first),
            const SizedBox(width: 12),
            Expanded(child: second),
          ],
        );
      },
    );
  }
}

class _DataCoverageCard extends StatelessWidget {
  const _DataCoverageCard({required this.coverage});

  final DataCoverage coverage;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.indigo[100]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.date_range, size: 16, color: Colors.indigo[700]),
              const SizedBox(width: 6),
              Text(
                '数据覆盖区间',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Colors.indigo[800],
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${coverage.start ?? "N/A"}  至  ${coverage.end ?? "N/A"}',
            style: TextStyle(
              color: Colors.grey[800],
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '跨度: ${coverage.spanDays != null ? "${coverage.spanDays} 天" : "未知"} '
            '· 样本: ${coverage.rows ?? 0}',
            style: TextStyle(fontSize: 12, color: Colors.grey[700]),
          ),
        ],
      ),
    );
  }
}
