/// Benchmark summary for compute governance operations.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import '../common/glass_card.dart';

class OperationComputeBenchmarkSummary extends StatelessWidget {
  const OperationComputeBenchmarkSummary({super.key, required this.operation});

  final JobRecord operation;

  @override
  Widget build(BuildContext context) {
    if (operation.type != 'compute_benchmark') {
      return const SizedBox.shrink();
    }

    final result = operation.result;
    final metrics = operation.metrics;
    final component = (result['component_label'] ?? result['component'] ?? '')
        .toString();
    final summary = (result['summary'] ?? '').toString();
    final pythonDuration =
        result['python_duration_ms'] ?? metrics['python_duration_ms'];
    final nativeDuration =
        result['native_duration_ms'] ?? metrics['native_duration_ms'];
    final vectorizedDuration =
        result['vectorized_duration_ms'] ?? metrics['vectorized_duration_ms'];
    final loopDuration =
        result['loop_duration_ms'] ?? metrics['loop_duration_ms'];
    final speedup = result['speedup_ratio'] ?? metrics['speedup_ratio'];

    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: GlassCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              component.isEmpty ? 'Benchmark 摘要' : '$component benchmark',
              style: AppTextStyles.labelMedium,
            ),
            if (summary.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                summary,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (pythonDuration != null)
                  _MetricPill(label: 'Python', value: '${pythonDuration}ms'),
                if (nativeDuration != null)
                  _MetricPill(label: 'Native', value: '${nativeDuration}ms'),
                if (vectorizedDuration != null)
                  _MetricPill(
                    label: 'Vectorized',
                    value: '${vectorizedDuration}ms',
                  ),
                if (loopDuration != null)
                  _MetricPill(label: 'Loop', value: '${loopDuration}ms'),
                if (speedup != null)
                  _MetricPill(label: 'Speedup', value: '${speedup}x'),
                if (operation.executionTarget?.isNotEmpty == true)
                  _MetricPill(
                    label: 'Worker',
                    value: operation.executionTarget!,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        '$label · $value',
        style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
      ),
    );
  }
}
