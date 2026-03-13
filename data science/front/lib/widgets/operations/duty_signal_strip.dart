/// 统一值班信号条
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';

class DutySignalStrip extends StatelessWidget {
  const DutySignalStrip({
    super.key,
    required this.summary,
    this.accent = AppColors.primary,
  });

  final DutySummary summary;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        _SignalChip(
          label: 'INCIDENT',
          value: '${summary.incidentCount}',
          foreground: summary.incidentCount > 0
              ? AppColors.error
              : AppColors.success,
          background: summary.incidentCount > 0
              ? AppColors.errorLight
              : AppColors.successLight,
        ),
        _SignalChip(
          label: 'ACTIVE',
          value: '${summary.activeCount}',
          foreground: AppColors.warning,
          background: AppColors.warningLight,
        ),
        _SignalChip(
          label: 'WATCH',
          value: '${summary.watchCount}',
          foreground: accent,
          background: accent.withValues(alpha: 0.12),
        ),
        _SignalChip(
          label: 'OVERDUE',
          value: '${summary.overdueCount}',
          foreground: summary.overdueCount > 0
              ? AppColors.error
              : AppColors.textSecondary,
          background: summary.overdueCount > 0
              ? AppColors.errorLight
              : AppColors.surfaceVariant,
        ),
        _SignalChip(
          label: 'ESCALATED',
          value: '${summary.escalatedCount}',
          foreground: summary.escalatedCount > 0
              ? AppColors.warning
              : AppColors.textSecondary,
          background: summary.escalatedCount > 0
              ? AppColors.warningLight
              : AppColors.surfaceVariant,
        ),
        _SignalChip(
          label: 'ALERTS',
          value: '${summary.alertCount}',
          foreground: AppColors.textPrimary,
          background: AppColors.surfaceVariant,
        ),
        if (summary.degradedSystemCount > 0)
          _SignalChip(
            label: 'SYSTEMS',
            value: '${summary.degradedSystemCount}',
            foreground: AppColors.warning,
            background: AppColors.warningLight,
          ),
      ],
    );
  }
}

class _SignalChip extends StatelessWidget {
  const _SignalChip({
    required this.label,
    required this.value,
    required this.foreground,
    required this.background,
  });

  final String label;
  final String value;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: foreground.withValues(alpha: 0.16)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: AppTextStyles.labelMedium.copyWith(color: foreground),
          ),
          const SizedBox(width: 8),
          Text(
            value,
            style: AppTextStyles.labelLarge.copyWith(color: foreground),
          ),
        ],
      ),
    );
  }
}
