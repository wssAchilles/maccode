library;

import 'package:flutter/material.dart';

import 'analysis_detail_support.dart';

class AnalysisStatisticalSection extends StatelessWidget {
  const AnalysisStatisticalSection({super.key, required this.statisticalTests});

  final Map<String, dynamic> statisticalTests;

  @override
  Widget build(BuildContext context) {
    final normalityTests = analysisDetailAsMap(
      statisticalTests['normality_tests'],
    );
    final nonNormalColumns = analysisDetailAsStringList(
      statisticalTests['non_normal_columns'],
    );
    final suggestions = analysisDetailAsStringList(
      statisticalTests['suggestions'],
    );

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (normalityTests != null && normalityTests.isNotEmpty) ...[
              const Text(
                '正态性检验',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              ...normalityTests.entries.map((entry) {
                final testResult = analysisDetailAsMap(entry.value);
                final isNormal = testResult?['is_normal'] as bool? ?? false;
                final pValue = analysisDetailAsNum(testResult?['p_value']);
                final skewness = analysisDetailAsNum(testResult?['skewness']);
                final kurtosis = analysisDetailAsNum(testResult?['kurtosis']);

                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isNormal
                        ? Colors.green.shade50
                        : Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: isNormal
                          ? Colors.green.shade200
                          : Colors.orange.shade200,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            isNormal ? Icons.check_circle : Icons.warning,
                            color: isNormal ? Colors.green : Colors.orange,
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              entry.key,
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          Text(
                            isNormal ? '正态分布' : '非正态分布',
                            style: TextStyle(
                              fontSize: 12,
                              color: isNormal ? Colors.green : Colors.orange,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _StatItem(
                            label: 'P值',
                            value: pValue?.toStringAsFixed(4) ?? '-',
                          ),
                          _StatItem(
                            label: '偏度',
                            value: skewness?.toStringAsFixed(3) ?? '-',
                          ),
                          _StatItem(
                            label: '峰度',
                            value: kurtosis?.toStringAsFixed(3) ?? '-',
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              }),
              const SizedBox(height: 16),
            ],
            if (nonNormalColumns.isNotEmpty) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, color: Colors.orange),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${nonNormalColumns.length} 列不符合正态分布',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (suggestions.isNotEmpty) ...[
              const Text(
                '统计建议',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              ...suggestions.map(
                (suggestion) => Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.auto_awesome,
                        size: 20,
                        color: Colors.purple,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          suggestion,
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

class _StatItem extends StatelessWidget {
  const _StatItem({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          label,
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}
