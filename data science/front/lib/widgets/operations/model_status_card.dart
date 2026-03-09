/// 模型状态卡
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';

class ModelStatusCard extends StatelessWidget {
  const ModelStatusCard({
    super.key,
    required this.title,
    required this.status,
    this.subtitle,
  });

  final String title;
  final SystemStatusItem status;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final color = switch (status.status) {
      'ok' => AppColors.success,
      'warning' => AppColors.warning,
      'error' => AppColors.error,
      _ => AppColors.textSecondary,
    };

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.memory_rounded, color: color),
              const SizedBox(width: 10),
              Expanded(child: Text(title, style: AppTextStyles.h4)),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            status.message,
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 10),
            Text(subtitle!, style: AppTextStyles.bodySmall),
          ],
        ],
      ),
    );
  }
}
