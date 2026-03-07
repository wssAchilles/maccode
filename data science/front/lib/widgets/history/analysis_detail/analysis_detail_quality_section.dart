library;

import 'package:flutter/material.dart';

import 'analysis_detail_support.dart';

class AnalysisQualitySection extends StatelessWidget {
  const AnalysisQualitySection({super.key, required this.qualityAnalysis});

  final Map<String, dynamic> qualityAnalysis;

  @override
  Widget build(BuildContext context) {
    final qualityScore = analysisDetailAsNum(qualityAnalysis['quality_score']);
    final qualityMetrics = analysisDetailAsMap(
      qualityAnalysis['quality_metrics'],
    );
    final recommendations = analysisDetailAsStringList(
      qualityAnalysis['recommendations'],
    );
    final highRiskColumns = analysisDetailAsStringList(
      qualityAnalysis['high_risk_columns'],
    );
    final missingRate = analysisDetailAsNum(qualityMetrics?['missing_rate']);

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (qualityScore != null) ...[
              Center(
                child: Column(
                  children: [
                    SizedBox(
                      width: 120,
                      height: 120,
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          SizedBox(
                            width: 120,
                            height: 120,
                            child: CircularProgressIndicator(
                              value: qualityScore / 100,
                              strokeWidth: 12,
                              backgroundColor: Colors.grey.shade200,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                analysisDetailQualityColor(qualityScore),
                              ),
                            ),
                          ),
                          Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                qualityScore.toStringAsFixed(1),
                                style: const TextStyle(
                                  fontSize: 32,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const Text(
                                '/ 100',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.grey,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      analysisDetailQualityLabel(qualityScore),
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: analysisDetailQualityColor(qualityScore),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
            ],
            if (qualityMetrics != null) ...[
              const Text(
                '质量指标',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              _MetricRow(
                label: '缺失率',
                value: missingRate != null
                    ? '${missingRate.toStringAsFixed(2)}%'
                    : '-',
              ),
              _MetricRow(
                label: '异常值数量',
                value: analysisDetailStringValue(
                  qualityMetrics['total_outliers'],
                ),
              ),
              _MetricRow(
                label: '重复行数',
                value: analysisDetailStringValue(
                  qualityMetrics['duplicate_rows'],
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (highRiskColumns.isNotEmpty) ...[
              const Text(
                '高风险列',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: highRiskColumns
                    .map(
                      (column) => Chip(
                        label: Text(column),
                        backgroundColor: Colors.orange.shade100,
                        labelStyle: const TextStyle(color: Colors.orange),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 16),
            ],
            if (recommendations.isNotEmpty) ...[
              const Text(
                '优化建议',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              ...recommendations.map(
                (recommendation) => Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.lightbulb_outline,
                        size: 20,
                        color: Colors.amber,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          recommendation,
                          style: const TextStyle(fontSize: 14),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(fontSize: 14, color: Colors.grey.shade700),
          ),
          Text(
            value,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
