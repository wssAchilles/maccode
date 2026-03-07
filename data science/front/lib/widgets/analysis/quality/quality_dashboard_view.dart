part of '../quality_dashboard.dart';

class QualityDashboard extends StatelessWidget {
  const QualityDashboard({super.key, required this.qualityAnalysis});

  final QualityAnalysis qualityAnalysis;

  double _sanitizeScore(double? score) {
    final resolvedScore = score ?? 0.0;
    if (!resolvedScore.isFinite) {
      return 0.0;
    }
    return resolvedScore.clamp(0.0, 100.0).toDouble();
  }

  Color _getScoreColor(double score) {
    if (score >= 80) return Colors.green;
    if (score >= 60) return Colors.orange;
    return Colors.red;
  }

  String _getScoreLabel(double score) {
    if (score >= 90) return '优秀';
    if (score >= 80) return '良好';
    if (score >= 70) return '中等';
    if (score >= 60) return '较差';
    return '不合格';
  }

  @override
  Widget build(BuildContext context) {
    if (!qualityAnalysis.success) {
      return _QualityErrorState(message: qualityAnalysis.message ?? '未知错误');
    }

    final score = _sanitizeScore(qualityAnalysis.qualityScore);
    final scoreColor = _getScoreColor(score);
    final scoreLabel = _getScoreLabel(score);
    final hasMetrics = qualityAnalysis.qualityMetrics != null;
    final hasHighRiskColumns =
        qualityAnalysis.highRiskColumns?.isNotEmpty ?? false;
    final hasRecommendations =
        qualityAnalysis.recommendations?.isNotEmpty ?? false;
    final hasDetails = hasMetrics || hasHighRiskColumns || hasRecommendations;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 420;

        return Card(
          elevation: 4,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                _QualityDashboardHeader(isCompact: isCompact),
                const SizedBox(height: 24),
                _QualityScoreSection(
                  score: score,
                  scoreColor: scoreColor,
                  scoreLabel: scoreLabel,
                  isCompact: isCompact,
                ),
                const SizedBox(height: 24),
                if (hasMetrics)
                  _QualityMetricsSummary(
                    metrics: qualityAnalysis.qualityMetrics!,
                  ),
                if (hasDetails) ...[
                  const SizedBox(height: 16),
                  const Divider(),
                  const SizedBox(height: 16),
                ] else
                  const _QualityEmptyDetails(),
                if (hasHighRiskColumns)
                  _HighRiskWarning(
                    highRiskColumns: qualityAnalysis.highRiskColumns!,
                  ),
                if (hasRecommendations)
                  _RecommendationsSection(
                    recommendations: qualityAnalysis.recommendations!,
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}
