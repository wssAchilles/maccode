/// Unified embedded page header for shell content pages.
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class EmbeddedPageHeader extends StatelessWidget {
  const EmbeddedPageHeader({
    super.key,
    required this.title,
    required this.description,
    this.trailing,
    this.badges = const <EmbeddedHeaderBadge>[],
  });

  final String title;
  final String description;
  final Widget? trailing;
  final List<EmbeddedHeaderBadge> badges;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 920;
          final titleBlock = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: AppTextStyles.h2),
              const SizedBox(height: 8),
              Text(
                description,
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              if (badges.isNotEmpty) ...[
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: badges
                      .map((badge) => _EmbeddedHeaderBadgeChip(badge: badge))
                      .toList(growable: false),
                ),
              ],
            ],
          );

          if (trailing == null) {
            return titleBlock;
          }

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                titleBlock,
                const SizedBox(height: 16),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: trailing!,
                ),
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: titleBlock),
              const SizedBox(width: 16),
              trailing!,
            ],
          );
        },
      ),
    );
  }
}

class EmbeddedHeaderBadge {
  const EmbeddedHeaderBadge({
    required this.label,
    required this.value,
    required this.accent,
    this.icon,
  });

  final String label;
  final String value;
  final Color accent;
  final IconData? icon;
}

class _EmbeddedHeaderBadgeChip extends StatelessWidget {
  const _EmbeddedHeaderBadgeChip({required this.badge});

  final EmbeddedHeaderBadge badge;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: badge.accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
        border: Border.all(color: badge.accent.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (badge.icon != null) ...[
            Icon(badge.icon, size: 14, color: badge.accent),
            const SizedBox(width: 8),
          ],
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: '${badge.label} · ',
                  style: AppTextStyles.labelMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                TextSpan(
                  text: badge.value,
                  style: AppTextStyles.labelMedium.copyWith(
                    color: badge.accent,
                    fontWeight: FontWeight.w700,
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
