/// 历史记录卡片组件
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/history_record.dart';
import '../common/glass_card.dart';

class HistoryRecordCard extends StatelessWidget {
  const HistoryRecordCard({
    super.key,
    required this.record,
    required this.isDeleting,
    required this.onOpen,
    required this.onDelete,
  });

  final HistoryRecord record;
  final bool isDeleting;
  final VoidCallback onOpen;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final scoreStyle = _HistoryScoreStyle.fromRecord(record);

    return GlassCard(
      padding: const EdgeInsets.all(16),
      onTap: onOpen,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(
                  Icons.description_rounded,
                  size: 20,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  record.filename,
                  style: AppTextStyles.labelLarge,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (scoreStyle != null) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: scoreStyle.color.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(
                      AppDecorations.radiusFull,
                    ),
                    border: Border.all(
                      color: scoreStyle.color.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(scoreStyle.icon, size: 14, color: scoreStyle.color),
                      const SizedBox(width: 4),
                      Text(
                        scoreStyle.label,
                        style: AppTextStyles.labelMedium.copyWith(
                          color: scoreStyle.color,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Icon(
                Icons.access_time_rounded,
                size: 14,
                color: AppColors.textMuted,
              ),
              const SizedBox(width: 6),
              Text(
                record.createdAt != null
                    ? DateFormat('yyyy-MM-dd HH:mm').format(record.createdAt!)
                    : '未知时间',
                style: AppTextStyles.bodySmall,
              ),
              const Spacer(),
              IconButton(
                key: ValueKey('history-delete-${record.id}'),
                icon: isDeleting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.delete_outline_rounded, size: 18),
                onPressed: (!record.hasValidId || isDeleting) ? null : onDelete,
                tooltip: isDeleting ? '删除中' : '删除',
                style: IconButton.styleFrom(
                  foregroundColor: AppColors.error,
                  backgroundColor: AppColors.errorLight,
                  padding: const EdgeInsets.all(8),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HistoryScoreStyle {
  const _HistoryScoreStyle({
    required this.color,
    required this.icon,
    required this.label,
  });

  final Color color;
  final IconData icon;
  final String label;

  static _HistoryScoreStyle? fromRecord(HistoryRecord record) {
    final qualityScore = record.qualityScore;
    if (qualityScore == null) {
      return null;
    }

    if (qualityScore >= 80) {
      return _HistoryScoreStyle(
        color: AppColors.success,
        icon: Icons.check_circle_rounded,
        label: qualityScore.toStringAsFixed(1),
      );
    }

    if (qualityScore >= 60) {
      return _HistoryScoreStyle(
        color: AppColors.warning,
        icon: Icons.warning_rounded,
        label: qualityScore.toStringAsFixed(1),
      );
    }

    return _HistoryScoreStyle(
      color: AppColors.error,
      icon: Icons.error_rounded,
      label: qualityScore.toStringAsFixed(1),
    );
  }
}
