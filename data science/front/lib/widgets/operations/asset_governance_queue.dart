/// Asset governance queue board
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';

class AssetGovernanceQueue extends StatelessWidget {
  const AssetGovernanceQueue({
    super.key,
    required this.items,
    required this.onAction,
    this.failureChains = const <AssetFailureChain>[],
    this.onFailureAction,
    this.title = '风险处置中心',
    this.description = '将资产缺口、失败链路和推荐动作收成统一治理队列。',
  });

  final List<AssetGovernanceItem> items;
  final ValueChanged<AssetGovernanceItem> onAction;
  final List<AssetFailureChain> failureChains;
  final ValueChanged<AssetFailureChain>? onFailureAction;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty && failureChains.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: AppTextStyles.h4),
        const SizedBox(height: 8),
        Text(
          description,
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 12),
        if (failureChains.isNotEmpty) ...[
          _SectionLabel(title: '失败链路'),
          const SizedBox(height: 12),
          _AdaptiveGrid(
            children: failureChains
                .map(
                  (chain) => _FailureChainCard(
                    chain: chain,
                    onAction: onFailureAction == null
                        ? null
                        : () => onFailureAction!(chain),
                  ),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: 16),
        ],
        if (items.isNotEmpty) ...[
          _SectionLabel(title: '治理项'),
          const SizedBox(height: 12),
          _AdaptiveGrid(
            children: items
                .map(
                  (item) => _GovernanceCard(
                    item: item,
                    onAction: () => onAction(item),
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ],
    );
  }
}

class _AdaptiveGrid extends StatelessWidget {
  const _AdaptiveGrid({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1040;
        if (compact) {
          return Column(
            children: [
              for (var i = 0; i < children.length; i++) ...[
                children[i],
                if (i < children.length - 1) const SizedBox(height: 12),
              ],
            ],
          );
        }

        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: children
              .map(
                (child) => SizedBox(
                  width: (constraints.maxWidth - 12) / 2,
                  child: child,
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(title, style: AppTextStyles.labelLarge);
  }
}

class _GovernanceCard extends StatelessWidget {
  const _GovernanceCard({required this.item, required this.onAction});

  final AssetGovernanceItem item;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    final tone = _GovernanceTone.fromRisk(item.riskLevel);
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
                    Text(item.label, style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      'latest v${item.latestVersion} · ${item.latestLabel}',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: tone.background,
                  borderRadius: BorderRadius.circular(
                    AppDecorations.radiusFull,
                  ),
                ),
                child: Text(
                  item.riskLevel.toUpperCase(),
                  style: AppTextStyles.labelMedium.copyWith(
                    color: tone.foreground,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _QueueBadge(
                label: item.workspaceTargetLabel,
                foreground: tone.foreground,
                background: tone.background,
              ),
              _QueueBadge(
                label: item.actionLabel,
                foreground: AppColors.textPrimary,
                background: AppColors.surfaceVariant,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            item.workspaceBrief,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 14),
          _MetricRow(label: '资产库存', value: '${item.assetCount}'),
          _MetricRow(label: '失败任务', value: '${item.failedJobs}'),
          _MetricRow(label: '最新血缘', value: item.lineageSummary),
          if (item.failureSummary != '--')
            _MetricRow(label: '失败来源', value: item.failureSummary),
          _MetricRow(label: '处置建议', value: item.recommendedAction),
          const SizedBox(height: 14),
          FilledButton.tonalIcon(
            onPressed: onAction,
            icon: Icon(tone.icon),
            label: Text(item.actionLabel),
          ),
        ],
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 72,
            child: Text(
              label,
              style: AppTextStyles.labelMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(child: Text(value, style: AppTextStyles.bodyMedium)),
        ],
      ),
    );
  }
}

class _QueueBadge extends StatelessWidget {
  const _QueueBadge({
    required this.label,
    required this.foreground,
    required this.background,
  });

  final String label;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelMedium.copyWith(color: foreground),
      ),
    );
  }
}

class _FailureChainCard extends StatelessWidget {
  const _FailureChainCard({required this.chain, this.onAction});

  final AssetFailureChain chain;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
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
                  color: AppColors.errorLight,
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(
                  Icons.error_outline_rounded,
                  color: AppColors.error,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(chain.label, style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      'v${chain.latestVersion} · ${chain.contextLabel}',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppColors.errorLight,
                  borderRadius: BorderRadius.circular(
                    AppDecorations.radiusFull,
                  ),
                ),
                child: Text(
                  chain.latestPhase.toUpperCase(),
                  style: AppTextStyles.labelMedium.copyWith(
                    color: AppColors.error,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _QueueBadge(
                label: chain.workspaceTargetLabel,
                foreground: AppColors.error,
                background: AppColors.errorLight,
              ),
              _QueueBadge(
                label: chain.actionLabel,
                foreground: AppColors.textPrimary,
                background: AppColors.surfaceVariant,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            chain.workspaceBrief,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 14),
          _MetricRow(label: '错误码', value: chain.errorCode),
          _MetricRow(label: '失败来源', value: chain.sourceSummary),
          _MetricRow(label: '链路血缘', value: chain.lineageSummary),
          _MetricRow(label: '失败摘要', value: chain.errorMessage),
          _MetricRow(
            label: '尝试次数',
            value: '${chain.attemptCount}/${chain.maxAttempts}',
          ),
          _MetricRow(label: '处置建议', value: chain.recommendedAction),
          if (onAction != null) ...[
            const SizedBox(height: 14),
            FilledButton.tonalIcon(
              onPressed: onAction,
              icon: const Icon(Icons.build_circle_outlined),
              label: Text(chain.actionLabel),
            ),
          ],
        ],
      ),
    );
  }
}

class _GovernanceTone {
  const _GovernanceTone({
    required this.foreground,
    required this.background,
    required this.icon,
  });

  final Color foreground;
  final Color background;
  final IconData icon;

  factory _GovernanceTone.fromRisk(String riskLevel) {
    switch (riskLevel) {
      case 'action':
        return const _GovernanceTone(
          foreground: AppColors.error,
          background: AppColors.errorLight,
          icon: Icons.error_outline_rounded,
        );
      case 'watch':
        return const _GovernanceTone(
          foreground: AppColors.warning,
          background: AppColors.warningLight,
          icon: Icons.warning_amber_rounded,
        );
      default:
        return const _GovernanceTone(
          foreground: AppColors.success,
          background: AppColors.successLight,
          icon: Icons.verified_rounded,
        );
    }
  }
}
