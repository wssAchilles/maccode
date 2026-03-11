/// Unified operational narrative board for the Operations Hub.
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';

class OperationsNarrativeBoard extends StatelessWidget {
  const OperationsNarrativeBoard({
    super.key,
    required this.summary,
    required this.onOpenChain,
  });

  final DashboardSummary summary;
  final ValueChanged<AssetChainSummary> onOpenChain;

  @override
  Widget build(BuildContext context) {
    final cards = _cards();
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1180;
        if (compact) {
          return Column(
            children: [
              for (var i = 0; i < cards.length; i++) ...[
                cards[i],
                if (i < cards.length - 1) const SizedBox(height: 12),
              ],
            ],
          );
        }

        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: cards
              .map(
                (card) => SizedBox(
                  width: (constraints.maxWidth - 12) / 2,
                  child: card,
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }

  List<Widget> _cards() {
    final configs = [
      _NarrativeConfig(
        key: 'dataset',
        icon: Icons.dataset_rounded,
        accent: AppColors.primary,
      ),
      _NarrativeConfig(
        key: 'model',
        icon: Icons.model_training_rounded,
        accent: AppColors.cta,
      ),
      _NarrativeConfig(
        key: 'knowledge',
        icon: Icons.account_tree_rounded,
        accent: AppColors.success,
      ),
      _NarrativeConfig(
        key: 'optimization',
        icon: Icons.bolt_rounded,
        accent: AppColors.warning,
      ),
    ];

    return configs
        .map((config) {
          final chain = summary.assetSummary.chainSummaries
              .cast<AssetChainSummary?>()
              .firstWhere(
                (item) => item?.key == config.key,
                orElse: () => null,
              );
          return _NarrativeCard(
            config: config,
            chain: chain,
            governance: summary.assetSummary.governance
                .cast<AssetGovernanceItem?>()
                .firstWhere(
                  (item) => item?.key == config.key,
                  orElse: () => null,
                ),
            failure: summary.assetSummary.failureChains
                .cast<AssetFailureChain?>()
                .firstWhere(
                  (item) => item?.key == config.key,
                  orElse: () => null,
                ),
            onTap: chain == null ? null : () => onOpenChain(chain),
          );
        })
        .toList(growable: false);
  }
}

class _NarrativeConfig {
  const _NarrativeConfig({
    required this.key,
    required this.icon,
    required this.accent,
  });

  final String key;
  final IconData icon;
  final Color accent;
}

class _NarrativeCard extends StatelessWidget {
  const _NarrativeCard({
    required this.config,
    required this.chain,
    required this.governance,
    required this.failure,
    this.onTap,
  });

  final _NarrativeConfig config;
  final AssetChainSummary? chain;
  final AssetGovernanceItem? governance;
  final AssetFailureChain? failure;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final tone = _NarrativeTone.fromRisk(
      failure != null ? 'action' : governance?.riskLevel ?? 'healthy',
      config.accent,
    );
    final focusBlock = _focusBlockFor(chain);

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: tone.background,
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: Icon(config.icon, size: 20, color: tone.foreground),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      chain?.label ?? governance?.label ?? '--',
                      style: AppTextStyles.h4,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      chain == null
                          ? '当前还没有登记到统一资产摘要。'
                          : 'latest v${chain!.latestVersion} · ${chain!.latestLabel}',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    if (chain != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        '${chain!.statusLabel} · ${chain!.workspaceTargetLabel} · ${chain!.incidentTargetLabel}',
                        style: AppTextStyles.bodySmall.copyWith(
                          color: config.accent,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              _NarrativeBadge(
                label: failure != null
                    ? 'FAIL'
                    : (governance?.riskLevel ?? 'healthy').toUpperCase(),
                foreground: tone.foreground,
                background: tone.background,
              ),
            ],
          ),
          const SizedBox(height: 14),
          _NarrativeBlock(
            title: '版本血缘',
            content:
                chain?.lineageSummary ?? governance?.lineageSummary ?? '--',
            accent: config.accent,
            highlighted: focusBlock == _NarrativeFocusBlock.lineage,
          ),
          if (chain != null) ...[
            const SizedBox(height: 10),
            _NarrativeBlock(
              title: '目标落点',
              content:
                  '${chain!.workspaceTargetLabel} · ${chain!.workspaceBrief}',
              accent: config.accent,
              highlighted: focusBlock == _NarrativeFocusBlock.target,
            ),
          ],
          const SizedBox(height: 10),
          _NarrativeBlock(
            title: '值班责任',
            content: chain == null
                ? '${governance?.ownerLabel ?? '--'} · SLA ${governance?.slaMinutes ?? 0}min · ${governance?.escalationLabel ?? '--'}'
                : '${chain!.ownerLabel} · SLA ${chain!.slaMinutes}min · ${chain!.escalationLabel}',
            accent: AppColors.info,
          ),
          if (chain != null) ...[
            const SizedBox(height: 10),
            _NarrativeBlock(
              title: '响应时限',
              content:
                  '${chain!.escalationStateLabel} · ${chain!.isOverdue ? 'overdue ${chain!.overdueMinutes}m' : 'elapsed ${chain!.elapsedMinutes}m'}${chain!.slaDeadlineAt == null ? '' : ' · due ${_formatDate(chain!.slaDeadlineAt)}'}',
              accent: chain!.isOverdue
                  ? AppColors.error
                  : chain!.escalationTier > 0
                  ? AppColors.warning
                  : AppColors.success,
              highlighted: focusBlock == _NarrativeFocusBlock.sla,
            ),
          ],
          const SizedBox(height: 10),
          _NarrativeBlock(
            title: '最近活动',
            content: chain == null || chain!.activityTitle == '--'
                ? '暂无审计活动'
                : '${chain!.activityTitle} · ${chain!.activitySource} · ${_formatDate(chain!.activityAt)}',
            accent: config.accent,
            highlighted: focusBlock == _NarrativeFocusBlock.activity,
          ),
          const SizedBox(height: 10),
          _NarrativeBlock(
            title: '活跃作业',
            content: chain == null || chain!.jobStatus == '--'
                ? '当前无活跃作业'
                : '${chain!.jobStatus} · ${chain!.jobPhase} · ${chain!.jobProgress}%',
            accent: chain == null || chain!.jobStatus == '--'
                ? config.accent
                : AppColors.cta,
            highlighted: focusBlock == _NarrativeFocusBlock.job,
          ),
          const SizedBox(height: 10),
          _NarrativeBlock(
            title: failure == null ? '当前处置' : '失败来源',
            content: failure == null
                ? (governance?.recommendedAction ?? '--')
                : '${chain?.failureSource ?? failure!.sourceSummary} · ${chain?.failurePhase ?? failure!.latestPhase}',
            accent: failure == null ? config.accent : AppColors.error,
            highlighted: focusBlock == _NarrativeFocusBlock.action,
          ),
          if ((chain?.timeline.isNotEmpty ?? false)) ...[
            const SizedBox(height: 10),
            _TimelineStack(nodes: chain!.timeline),
          ],
          if (failure != null) ...[
            const SizedBox(height: 10),
            _NarrativeBlock(
              title: '失败摘要',
              content:
                  '${failure!.errorCode} · ${failure!.errorMessage} · ${failure!.attemptCount}/${failure!.maxAttempts}',
              accent: AppColors.error,
            ),
          ],
          const SizedBox(height: 14),
          FilledButton.tonalIcon(
            onPressed: onTap,
            icon: Icon(
              failure == null
                  ? Icons.arrow_outward_rounded
                  : Icons.build_circle_outlined,
            ),
            label: Text(
              failure?.actionLabel ?? governance?.actionLabel ?? '打开工作台',
            ),
          ),
        ],
      ),
    );
  }
}

class _NarrativeBlock extends StatelessWidget {
  const _NarrativeBlock({
    required this.title,
    required this.content,
    required this.accent,
    this.highlighted = false,
  });

  final String title;
  final String content;
  final Color accent;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: highlighted
            ? Color.alphaBlend(
                accent.withValues(alpha: 0.06),
                AppColors.surfaceVariant,
              )
            : AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(
          color: accent.withValues(alpha: highlighted ? 0.22 : 0.12),
          width: highlighted ? 1.3 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 6),
          Text(content, style: AppTextStyles.bodyMedium),
        ],
      ),
    );
  }
}

class _TimelineStack extends StatelessWidget {
  const _TimelineStack({required this.nodes});

  final List<AssetChainNode> nodes;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '链路时间线',
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          for (var i = 0; i < nodes.length; i++) ...[
            _TimelineNodeTile(node: nodes[i]),
            if (i < nodes.length - 1) const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _TimelineNodeTile extends StatelessWidget {
  const _TimelineNodeTile({required this.node});

  final AssetChainNode node;

  @override
  Widget build(BuildContext context) {
    final tone = _nodeTone(node.level);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 10,
          height: 10,
          margin: const EdgeInsets.only(top: 5),
          decoration: BoxDecoration(
            color: tone,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(node.title, style: AppTextStyles.labelLarge),
              const SizedBox(height: 4),
              Text(
                _timelineDetail(node),
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Text(
          _formatDate(node.timestamp),
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}

class _NarrativeBadge extends StatelessWidget {
  const _NarrativeBadge({
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

class _NarrativeTone {
  const _NarrativeTone({required this.foreground, required this.background});

  final Color foreground;
  final Color background;

  factory _NarrativeTone.fromRisk(String riskLevel, Color accent) {
    switch (riskLevel) {
      case 'action':
        return const _NarrativeTone(
          foreground: AppColors.error,
          background: AppColors.errorLight,
        );
      case 'watch':
        return const _NarrativeTone(
          foreground: AppColors.warning,
          background: AppColors.warningLight,
        );
      default:
        return _NarrativeTone(
          foreground: accent,
          background: accent.withValues(alpha: 0.12),
        );
    }
  }
}

String _formatDate(DateTime? value) {
  if (value == null) {
    return '--';
  }
  return DateFormat('MM-dd HH:mm').format(value.toLocal());
}

Color _nodeTone(String level) {
  switch (level) {
    case 'error':
      return AppColors.error;
    case 'warning':
      return AppColors.warning;
    default:
      return AppColors.primary;
  }
}

String _timelineDetail(AssetChainNode node) {
  final segments = <String>[
    if (node.badge != '--') node.badge,
    if (node.phaseLabel != '--') node.phaseLabel,
    if (node.sourceLabel != '--') node.sourceLabel,
    if (node.versionTag != '--') 'v${node.versionTag}',
    node.detail,
  ];
  return segments.join(' · ');
}

_NarrativeFocusBlock _focusBlockFor(AssetChainSummary? chain) {
  if (chain == null) {
    return _NarrativeFocusBlock.lineage;
  }
  switch (chain.narrativeTarget) {
    case 'lineage':
      return _NarrativeFocusBlock.lineage;
    case 'sla':
      return _NarrativeFocusBlock.sla;
    case 'activity':
      return _NarrativeFocusBlock.activity;
    case 'job':
      return _NarrativeFocusBlock.job;
    case 'action':
      return _NarrativeFocusBlock.action;
    case 'target':
    default:
      return _NarrativeFocusBlock.target;
  }
}

enum _NarrativeFocusBlock { lineage, target, sla, activity, job, action }
