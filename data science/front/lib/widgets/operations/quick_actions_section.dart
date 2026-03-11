/// 快捷动作区
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class QuickActionsSection extends StatelessWidget {
  const QuickActionsSection({super.key, required this.actions});

  final List<QuickActionItem> actions;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('快捷动作', style: AppTextStyles.h4),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth >= 1100;
              final cardWidth = wide ? (constraints.maxWidth - 24) / 3 : 240.0;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: actions
                    .map(
                      (item) => SizedBox(
                        width: cardWidth,
                        child: _QuickActionCard(item: item),
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }
}

class QuickActionItem {
  const QuickActionItem({
    required this.label,
    required this.icon,
    required this.onTap,
    required this.description,
    this.emphasis = false,
    this.contextLabel,
    this.actionLabel = '打开工作台',
    this.accent,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final String description;
  final bool emphasis;
  final String? contextLabel;
  final String actionLabel;
  final Color? accent;
}

class _QuickActionCard extends StatelessWidget {
  const _QuickActionCard({required this.item});

  final QuickActionItem item;

  @override
  Widget build(BuildContext context) {
    final accent =
        item.accent ?? (item.emphasis ? AppColors.cta : AppColors.primary);
    final background = item.emphasis
        ? const LinearGradient(
            colors: [Color(0xFFF38B2A), Color(0xFFF5A341)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          )
        : null;
    final foreground = item.emphasis ? Colors.white : AppColors.textPrimary;

    return GlassCard(
      onTap: item.onTap,
      padding: const EdgeInsets.all(18),
      gradient: background,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: item.emphasis
                      ? Colors.white.withValues(alpha: 0.18)
                      : accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: Icon(
                  item.icon,
                  color: item.emphasis ? Colors.white : accent,
                  size: 20,
                ),
              ),
              const Spacer(),
              if (item.contextLabel != null && item.contextLabel!.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: item.emphasis
                        ? Colors.white.withValues(alpha: 0.14)
                        : AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(
                      AppDecorations.radiusFull,
                    ),
                  ),
                  child: Text(
                    item.contextLabel!,
                    style: AppTextStyles.labelMedium.copyWith(
                      color: foreground,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            item.label,
            style: AppTextStyles.labelLarge.copyWith(color: foreground),
          ),
          const SizedBox(height: 8),
          Text(
            item.description,
            style: AppTextStyles.bodySmall.copyWith(
              color: item.emphasis
                  ? Colors.white.withValues(alpha: 0.92)
                  : AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Text(
                item.actionLabel,
                style: AppTextStyles.labelMedium.copyWith(color: foreground),
              ),
              const SizedBox(width: 6),
              Icon(Icons.arrow_outward_rounded, size: 16, color: foreground),
            ],
          ),
        ],
      ),
    );
  }
}
