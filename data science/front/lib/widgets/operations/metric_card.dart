/// KPI 指标卡
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class MetricCard extends StatelessWidget {
  const MetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.supportingText,
    this.emphasis = false,
  });

  final String label;
  final String value;
  final IconData icon;
  final String? supportingText;
  final bool emphasis;

  @override
  Widget build(BuildContext context) {
    final accent = emphasis ? AppColors.cta : AppColors.primary;
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: Icon(icon, color: accent, size: 20),
              ),
              const Spacer(),
              Text(label, style: AppTextStyles.labelMedium),
            ],
          ),
          const SizedBox(height: 18),
          Text(value, style: AppTextStyles.h2),
          if (supportingText != null) ...[
            const SizedBox(height: 6),
            Text(
              supportingText!,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
