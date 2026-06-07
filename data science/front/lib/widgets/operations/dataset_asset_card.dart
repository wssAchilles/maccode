/// 数据资产卡
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';

class DatasetAssetCard extends StatelessWidget {
  const DatasetAssetCard({super.key, required this.asset});

  final DatasetAsset asset;

  @override
  Widget build(BuildContext context) {
    final qualityScore = asset.qualityScore;
    final qualityColor = qualityScore == null
        ? AppColors.textMuted
        : qualityScore >= 80
        ? AppColors.success
        : qualityScore >= 60
        ? AppColors.warning
        : AppColors.error;

    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(
                  Icons.dataset_rounded,
                  color: AppColors.primary,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  asset.filename,
                  style: AppTextStyles.labelLarge,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            asset.createdAt == null
                ? '时间未知'
                : DateFormat(
                    'yyyy-MM-dd HH:mm',
                  ).format(asset.createdAt!.toLocal()),
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Text('质量评分', style: AppTextStyles.labelMedium),
              const Spacer(),
              Text(
                qualityScore?.toStringAsFixed(1) ?? '--',
                style: AppTextStyles.labelLarge.copyWith(color: qualityColor),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
