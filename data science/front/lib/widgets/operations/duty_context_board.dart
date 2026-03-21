/// 统一值班控制板
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class DutyContextBoard extends StatelessWidget {
  const DutyContextBoard({
    super.key,
    required this.title,
    required this.description,
    required this.icon,
    required this.metrics,
    this.signalStrip,
    required this.currentWatch,
    this.contextFacts = const [],
    this.footerTitle,
    this.footer,
    this.accent = AppColors.primary,
  });

  final String title;
  final String description;
  final IconData icon;
  final List<DutyMetric> metrics;
  final Widget? signalStrip;
  final String currentWatch;
  final List<DutyContextFact> contextFacts;
  final String? footerTitle;
  final Widget? footer;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
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
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      description,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (metrics.isNotEmpty) ...[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: metrics
                  .map((metric) => _DutyMetricChip(metric: metric))
                  .toList(growable: false),
            ),
          ],
          if (signalStrip != null) ...[
            const SizedBox(height: 14),
            signalStrip!,
          ],
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('当前关注', style: AppTextStyles.labelMedium),
                const SizedBox(height: 6),
                Text(
                  currentWatch,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                if (contextFacts.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: contextFacts
                        .map((fact) => _DutyContextChip(fact: fact))
                        .toList(growable: false),
                  ),
                ],
              ],
            ),
          ),
          if (footer != null) ...[
            const SizedBox(height: 16),
            if ((footerTitle ?? '').isNotEmpty) ...[
              Text(footerTitle!, style: AppTextStyles.labelLarge),
              const SizedBox(height: 10),
            ],
            footer!,
          ],
        ],
      ),
    );
  }
}

class DutyMetric {
  const DutyMetric({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;
}

class DutyContextFact {
  const DutyContextFact({
    required this.label,
    required this.value,
    this.icon,
    this.foreground = AppColors.textSecondary,
    this.background = AppColors.background,
  });

  final String label;
  final String value;
  final IconData? icon;
  final Color foreground;
  final Color background;
}

class _DutyMetricChip extends StatelessWidget {
  const _DutyMetricChip({required this.metric});

  final DutyMetric metric;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: metric.color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: metric.color.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            metric.label,
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            metric.value,
            style: AppTextStyles.labelLarge.copyWith(color: metric.color),
          ),
        ],
      ),
    );
  }
}

class _DutyContextChip extends StatelessWidget {
  const _DutyContextChip({required this.fact});

  final DutyContextFact fact;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: fact.background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (fact.icon != null) ...[
            Icon(fact.icon, size: 14, color: fact.foreground),
            const SizedBox(width: 6),
          ],
          Text(
            '${fact.label} · ${fact.value}',
            style: AppTextStyles.labelMedium.copyWith(color: fact.foreground),
          ),
        ],
      ),
    );
  }
}
