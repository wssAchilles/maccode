/// 数据质量仪表板组件
/// 显示质量分数和建议
library;

import 'package:flutter/material.dart';
import 'package:percent_indicator/percent_indicator.dart';
import '../../models/analysis_result.dart';

class QualityDashboard extends StatelessWidget {
  final QualityAnalysis qualityAnalysis;

  const QualityDashboard({
    super.key,
    required this.qualityAnalysis,
  });

  @override
  Widget build(BuildContext context) {
    // 如果分析失败，显示错误
    if (!qualityAnalysis.success) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 8),
              Text(
                '质量检查失败',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                qualityAnalysis.message ?? '未知错误',
                style: const TextStyle(color: Colors.red),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    final score = qualityAnalysis.qualityScore ?? 0.0;
    final Color scoreColor = _getScoreColor(score);
    final String scoreLabel = _getScoreLabel(score);

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // 标题
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.assessment, size: 28),
                const SizedBox(width: 8),
                Text(
                  '数据质量评估',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // 质量分数圆形进度条
            CircularPercentIndicator(
              radius: 80.0,
              lineWidth: 16.0,
              percent: score / 100,
              center: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    score.toStringAsFixed(1),
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      color: scoreColor,
                    ),
                  ),
                  const Text(
                    '/ 100',
                    style: TextStyle(
                      fontSize: 16,
                      color: Colors.grey,
                    ),
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
            
            // 分数标签
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: scoreColor.withOpacity(0.1),
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
            const SizedBox(height: 24),

            // 质量指标摘要
            if (qualityAnalysis.qualityMetrics != null)
              _buildMetricsSummary(context, qualityAnalysis.qualityMetrics!),

            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),

            // 高风险列警告
            if (qualityAnalysis.highRiskColumns != null &&
                qualityAnalysis.highRiskColumns!.isNotEmpty)
              _buildHighRiskWarning(context, qualityAnalysis.highRiskColumns!),

            // 建议列表
            if (qualityAnalysis.recommendations != null &&
                qualityAnalysis.recommendations!.isNotEmpty)
              _buildRecommendations(context, qualityAnalysis.recommendations!),
          ],
        ),
      ),
    );
  }

  /// 根据分数获取颜色
  Color _getScoreColor(double score) {
    if (score >= 80) return Colors.green;
    if (score >= 60) return Colors.orange;
    return Colors.red;
  }

  /// 根据分数获取标签
  String _getScoreLabel(double score) {
    if (score >= 90) return '优秀';
    if (score >= 80) return '良好';
    if (score >= 70) return '中等';
    if (score >= 60) return '较差';
    return '不合格';
  }

  /// 构建指标摘要
  Widget _buildMetricsSummary(BuildContext context, QualityMetrics metrics) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          _buildMetricRow(
            context,
            Icons.grid_on,
            '总单元格',
            metrics.totalCells.toString(),
            Colors.blue,
          ),
          const SizedBox(height: 8),
          _buildMetricRow(
            context,
            Icons.block,
            '缺失值',
            '${metrics.totalMissing} (${metrics.missingRate.toStringAsFixed(1)}%)',
            metrics.missingRate > 5 ? Colors.red : Colors.green,
          ),
          const SizedBox(height: 8),
          _buildMetricRow(
            context,
            Icons.warning_amber,
            '异常值',
            metrics.totalOutliers.toString(),
            metrics.totalOutliers > 0 ? Colors.orange : Colors.green,
          ),
          const SizedBox(height: 8),
          _buildMetricRow(
            context,
            Icons.copy,
            '重复行',
            metrics.duplicateRows.toString(),
            metrics.duplicateRows > 0 ? Colors.orange : Colors.green,
          ),
        ],
      ),
    );
  }

  /// 构建单个指标行
  Widget _buildMetricRow(
    BuildContext context,
    IconData icon,
    String label,
    String value,
    Color color,
  ) {
    return Row(
      children: [
        Icon(icon, size: 20, color: color),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(fontSize: 14),
          ),
        ),
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

  /// 构建高风险列警告
  Widget _buildHighRiskWarning(BuildContext context, List<String> highRiskColumns) {
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
                .map((col) => Chip(
                      label: Text(col),
                      backgroundColor: Colors.red.shade100,
                      deleteIcon: const Icon(Icons.error_outline, size: 16),
                      onDeleted: () {}, // 仅作展示，不删除
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }

  /// 构建建议列表
  Widget _buildRecommendations(BuildContext context, List<String> recommendations) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.lightbulb_outline, color: Colors.amber),
            const SizedBox(width: 8),
            Text(
              '改进建议',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ...recommendations.asMap().entries.map((entry) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 8.0),
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
