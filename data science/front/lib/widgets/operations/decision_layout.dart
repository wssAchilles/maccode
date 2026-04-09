library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../common/glass_card.dart';

class DecisionHeaderMetric {
  const DecisionHeaderMetric({
    required this.label,
    required this.value,
    required this.accent,
    this.icon,
    this.helper,
  });

  final String label;
  final String value;
  final Color accent;
  final IconData? icon;
  final String? helper;
}

class DecisionHeaderAction {
  const DecisionHeaderAction({
    required this.label,
    required this.icon,
    required this.onTap,
    this.isPrimary = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final bool isPrimary;
}

class DecisionHeaderCard extends StatelessWidget {
  const DecisionHeaderCard({
    super.key,
    required this.title,
    required this.summary,
    required this.metrics,
    this.primaryAction,
    this.secondaryActions = const <DecisionHeaderAction>[],
    this.banner,
  });

  final String title;
  final String summary;
  final List<DecisionHeaderMetric> metrics;
  final DecisionHeaderAction? primaryAction;
  final List<DecisionHeaderAction> secondaryActions;
  final Widget? banner;

  @override
  Widget build(BuildContext context) {
    final visibleMetrics = metrics.take(4).toList(growable: false);

    return GlassCard(
      padding: const EdgeInsets.all(24),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 980;
          final metricColumns = constraints.maxWidth >= 1200
              ? 4
              : constraints.maxWidth >= 680
              ? 2
              : 1;

          final headerBlock = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: AppTextStyles.h2),
              const SizedBox(height: 8),
              Text(
                summary,
                style: AppTextStyles.bodyLarge.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          );

          final actions = <Widget>[
            if (primaryAction != null)
              _DecisionActionButton(action: primaryAction!, emphasized: true),
            for (final action in secondaryActions)
              _DecisionActionButton(action: action),
          ];

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (compact)
                headerBlock
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: headerBlock),
                    if (actions.isNotEmpty) ...[
                      const SizedBox(width: 20),
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 360),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: actions
                              .map(
                                (action) => Padding(
                                  padding: const EdgeInsets.only(bottom: 10),
                                  child: action,
                                ),
                              )
                              .toList(growable: false),
                        ),
                      ),
                    ],
                  ],
                ),
              if (compact && actions.isNotEmpty) ...[
                const SizedBox(height: 18),
                Wrap(spacing: 10, runSpacing: 10, children: actions),
              ],
              if (banner != null) ...[const SizedBox(height: 18), banner!],
              if (visibleMetrics.isNotEmpty) ...[
                const SizedBox(height: 20),
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: visibleMetrics.length,
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: metricColumns,
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: metricColumns == 1 ? 3.3 : 2.1,
                  ),
                  itemBuilder: (context, index) =>
                      _DecisionMetricCard(metric: visibleMetrics[index]),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class PrimaryWorkflowPanel extends StatelessWidget {
  const PrimaryWorkflowPanel({
    super.key,
    required this.title,
    required this.summary,
    required this.child,
    this.eyebrow,
    this.trailing,
  });

  final String title;
  final String summary;
  final Widget child;
  final String? eyebrow;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if ((eyebrow ?? '').isNotEmpty) ...[
                      Text(
                        eyebrow!,
                        style: AppTextStyles.labelMedium.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 8),
                    ],
                    Text(title, style: AppTextStyles.h3),
                    const SizedBox(height: 6),
                    Text(
                      summary,
                      style: AppTextStyles.bodyMedium.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              if (trailing != null) ...[const SizedBox(width: 16), trailing!],
            ],
          ),
          const SizedBox(height: 20),
          child,
        ],
      ),
    );
  }
}

class ProgressiveDetailSection extends StatelessWidget {
  const ProgressiveDetailSection({
    super.key,
    required this.title,
    required this.summary,
    required this.child,
    this.icon,
    this.initiallyExpanded = false,
    this.badge,
  });

  final String title;
  final String summary;
  final Widget child;
  final IconData? icon;
  final bool initiallyExpanded;
  final Widget? badge;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: EdgeInsets.zero,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          childrenPadding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          initiallyExpanded: initiallyExpanded,
          shape: const RoundedRectangleBorder(side: BorderSide.none),
          collapsedShape: const RoundedRectangleBorder(side: BorderSide.none),
          leading: icon == null
              ? null
              : Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppColors.infoLight,
                    borderRadius: BorderRadius.circular(
                      AppDecorations.radiusMd,
                    ),
                  ),
                  child: Icon(icon, color: AppColors.primary),
                ),
          title: Text(title, style: AppTextStyles.h4),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              summary,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          trailing:
              badge ??
              const Icon(
                Icons.expand_more_rounded,
                color: AppColors.textSecondary,
              ),
          children: [child],
        ),
      ),
    );
  }
}

class DecisionBanner extends StatelessWidget {
  const DecisionBanner({
    super.key,
    required this.title,
    required this.message,
    required this.accent,
    this.icon,
  });

  final String title;
  final String message;
  final Color accent;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: accent.withValues(alpha: 0.14)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Icon(
              icon ?? Icons.info_outline_rounded,
              size: 18,
              color: accent,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTextStyles.labelLarge.copyWith(color: accent),
                ),
                const SizedBox(height: 4),
                Text(
                  message,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textPrimary,
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

class _DecisionMetricCard extends StatelessWidget {
  const _DecisionMetricCard({required this.metric});

  final DecisionHeaderMetric metric;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: metric.accent.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              if (metric.icon != null) ...[
                Icon(metric.icon, size: 16, color: metric.accent),
                const SizedBox(width: 8),
              ],
              Expanded(
                child: Text(
                  metric.label,
                  style: AppTextStyles.labelMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            metric.value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.h3.copyWith(color: metric.accent),
          ),
          if ((metric.helper ?? '').isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              metric.helper!,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _DecisionActionButton extends StatelessWidget {
  const _DecisionActionButton({required this.action, this.emphasized = false});

  final DecisionHeaderAction action;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    if (emphasized || action.isPrimary) {
      return FilledButton.icon(
        onPressed: action.onTap,
        icon: Icon(action.icon),
        label: Text(action.label),
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.cta,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
          ),
        ),
      );
    }

    return OutlinedButton.icon(
      onPressed: action.onTap,
      icon: Icon(action.icon),
      label: Text(action.label),
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
      ),
    );
  }
}
