library;

import 'package:flutter/material.dart';

import 'analysis_detail_support.dart';

class AnalysisCorrelationSection extends StatelessWidget {
  const AnalysisCorrelationSection({
    super.key,
    required this.correlationAnalysis,
  });

  final Map<String, dynamic> correlationAnalysis;

  @override
  Widget build(BuildContext context) {
    final correlationEntries = buildAnalysisCorrelationEntries(
      correlationAnalysis,
    );
    final suggestions = analysisDetailAsStringList(
      correlationAnalysis['suggestions'],
    );

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (correlationEntries.isNotEmpty) ...[
              const Text(
                '高相关性变量对',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              ...correlationEntries.map(
                (entry) => Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          entry.label,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: analysisDetailCorrelationColor(
                            entry.correlation,
                          ),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          entry.correlation.toStringAsFixed(3),
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (suggestions.isNotEmpty) ...[
              const Text(
                '分析建议',
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
                        Icons.tips_and_updates,
                        size: 20,
                        color: Colors.blue,
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
