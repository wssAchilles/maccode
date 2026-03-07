library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'analysis_detail_support.dart';

class AnalysisDetailEmptyState extends StatelessWidget {
  const AnalysisDetailEmptyState({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 64, color: Colors.grey),
          SizedBox(height: 16),
          Text('无可用数据', style: TextStyle(fontSize: 18, color: Colors.grey)),
        ],
      ),
    );
  }
}

class AnalysisSectionTitle extends StatelessWidget {
  const AnalysisSectionTitle({
    super.key,
    required this.title,
    required this.icon,
  });

  final String title;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 24, color: Colors.blue),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}

class AnalysisFileInfoCard extends StatelessWidget {
  const AnalysisFileInfoCard({
    super.key,
    required this.filename,
    required this.dateTime,
    required this.basicInfo,
    required this.qualityScore,
  });

  final String filename;
  final DateTime? dateTime;
  final Map<String, dynamic>? basicInfo;
  final double? qualityScore;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.insert_drive_file,
                  size: 32,
                  color: Colors.blue,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        filename,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (dateTime != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          '分析时间: ${DateFormat('yyyy-MM-dd HH:mm:ss').format(dateTime!)}',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (qualityScore != null) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: analysisDetailQualityColor(qualityScore!),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '${qualityScore!.toStringAsFixed(1)}分',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ],
            ),
            if (basicInfo != null) ...[
              const Divider(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _InfoItem(
                    icon: Icons.table_rows,
                    label: '行数',
                    value: analysisDetailStringValue(basicInfo?['rows']),
                  ),
                  _InfoItem(
                    icon: Icons.view_column,
                    label: '列数',
                    value: analysisDetailStringValue(basicInfo?['columns']),
                  ),
                  _InfoItem(
                    icon: Icons.memory,
                    label: '内存',
                    value: analysisDetailStringValue(
                      basicInfo?['memory_usage'],
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _InfoItem extends StatelessWidget {
  const _InfoItem({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, size: 24, color: Colors.blue),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}
