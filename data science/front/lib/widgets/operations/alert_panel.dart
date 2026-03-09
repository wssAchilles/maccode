/// 驾驶舱告警卡
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';

class AlertPanel extends StatelessWidget {
  const AlertPanel({super.key, required this.alert});

  final DashboardAlert alert;

  @override
  Widget build(BuildContext context) {
    final tone = _AlertTone.fromSeverity(alert.severity);
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: tone.background,
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Icon(tone.icon, color: tone.foreground, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(alert.title, style: AppTextStyles.labelLarge),
                const SizedBox(height: 4),
                Text(
                  alert.message,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AlertTone {
  const _AlertTone({
    required this.foreground,
    required this.background,
    required this.icon,
  });

  final Color foreground;
  final Color background;
  final IconData icon;

  factory _AlertTone.fromSeverity(String severity) {
    switch (severity) {
      case 'error':
        return const _AlertTone(
          foreground: AppColors.error,
          background: AppColors.errorLight,
          icon: Icons.error_outline_rounded,
        );
      case 'warning':
        return const _AlertTone(
          foreground: AppColors.warning,
          background: AppColors.warningLight,
          icon: Icons.warning_amber_rounded,
        );
      default:
        return const _AlertTone(
          foreground: AppColors.primary,
          background: AppColors.infoLight,
          icon: Icons.info_outline_rounded,
        );
    }
  }
}
