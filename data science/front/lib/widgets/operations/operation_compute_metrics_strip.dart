/// Operation compute telemetry strip.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../utils/operation_compute_metrics.dart';

class OperationComputeMetricsStrip extends StatelessWidget {
  const OperationComputeMetricsStrip({
    super.key,
    required this.metrics,
    this.compact = false,
  });

  final Map<String, dynamic> metrics;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final items = extractOperationComputeMetrics(metrics);
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 0 : 12,
        vertical: compact ? 0 : 10,
      ),
      decoration: compact
          ? null
          : BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
            ),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: items.map((item) {
          return _ComputePill(item: item, compact: compact);
        }).toList(growable: false),
      ),
    );
  }
}

class _ComputePill extends StatelessWidget {
  const _ComputePill({
    required this.item,
    required this.compact,
  });

  final OperationComputeMetric item;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final tone = item.backend == 'native_cpp'
        ? (AppColors.success, AppColors.successLight)
        : (AppColors.primary, AppColors.infoLight);
    final contextLabel = item.context.isEmpty ? '--' : item.context;
    final rolloutLabel = item.rolloutMode.isEmpty ? '--' : item.rolloutMode;
    final benchmarkLabel = item.benchmarkStatus.isEmpty
        ? (item.benchmarkReady ? 'benchmark ready' : 'benchmark pending')
        : 'benchmark ${item.benchmarkStatus}';
    final guardLabel = item.guardFailureThreshold > 0
        ? 'guard ${item.guardRecentFailureCount}/${item.guardFailureThreshold}'
        : 'guard --';
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 0 : 10,
        vertical: compact ? 0 : 8,
      ),
      decoration: compact
          ? null
          : BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              border: Border.all(color: tone.$2.withValues(alpha: 0.9)),
            ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            item.label,
            style: AppTextStyles.labelMedium.copyWith(color: tone.$1),
          ),
          if (!compact) const SizedBox(height: 2),
          Text(
            '${item.durationMs.toStringAsFixed(1)}ms · ${item.backend}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (!compact)
            Text(
              'Rows ${item.rows} · $contextLabel · $rolloutLabel · $benchmarkLabel · $guardLabel',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
            ),
          if (!compact && item.rolloutReason.isNotEmpty)
            Text(
              item.rolloutReason,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          if (!compact && item.benchmarkSummary.isNotEmpty)
            Text(
              item.benchmarkSpeedupRatio == null
                  ? item.benchmarkSummary
                  : '${item.benchmarkSummary} · ${item.benchmarkSpeedupRatio!.toStringAsFixed(2)}x',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
            ),
          if (!compact && item.fallbackReason.isNotEmpty)
            Text(
              'fallback · ${item.fallbackReason}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.warning,
              ),
            ),
          if (!compact && item.guardAutoRollbackApplied)
            Text(
              'auto rollback · ${item.guardLastAutoRollbackReason.isEmpty ? "stable python" : item.guardLastAutoRollbackReason}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.warning,
              ),
            ),
        ],
      ),
    );
  }
}
