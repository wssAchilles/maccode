part of '../glass_card.dart';

/// 统计数值卡片 - 用于展示关键指标
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.value,
    required this.label,
    this.icon,
    this.trend,
    this.trendValue,
    this.gradient,
    this.onTap,
  });

  final String value;
  final String label;
  final IconData? icon;
  final TrendDirection? trend;
  final String? trendValue;
  final LinearGradient? gradient;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      gradient: gradient,
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (icon != null)
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: gradient != null
                        ? Colors.white.withValues(alpha: 0.2)
                        : AppColors.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(
                      AppDecorations.radiusMd,
                    ),
                  ),
                  child: Icon(
                    icon,
                    size: 20,
                    color: gradient != null ? Colors.white : AppColors.primary,
                  ),
                ),
              if (trend != null && trendValue != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: _getTrendColor().withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(
                      AppDecorations.radiusFull,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(_getTrendIcon(), size: 12, color: _getTrendColor()),
                      const SizedBox(width: 4),
                      Text(
                        trendValue!,
                        style: AppTextStyles.labelMedium.copyWith(
                          color: _getTrendColor(),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            value,
            style: AppTextStyles.h2.copyWith(
              color: gradient != null ? Colors.white : AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: gradient != null
                  ? Colors.white.withValues(alpha: 0.8)
                  : AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }

  Color _getTrendColor() {
    switch (trend) {
      case TrendDirection.up:
        return AppColors.success;
      case TrendDirection.down:
        return AppColors.error;
      case TrendDirection.neutral:
      case null:
        return AppColors.textMuted;
    }
  }

  IconData _getTrendIcon() {
    switch (trend) {
      case TrendDirection.up:
        return Icons.trending_up_rounded;
      case TrendDirection.down:
        return Icons.trending_down_rounded;
      case TrendDirection.neutral:
      case null:
        return Icons.trending_flat_rounded;
    }
  }
}

/// 趋势方向枚举
enum TrendDirection { up, down, neutral }
