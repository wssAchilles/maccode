/// Operations Hub asset version timeline board
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';
import 'workspace_action_lane.dart';

class AssetVersionTimelineBoard extends StatelessWidget {
  const AssetVersionTimelineBoard({
    super.key,
    required this.summary,
    required this.onNavigateToTab,
    this.dutySummary,
  });

  final AssetSummary summary;
  final ValueChanged<int> onNavigateToTab;
  final DutySummary? dutySummary;

  @override
  Widget build(BuildContext context) {
    final lanes =
        [
          _TimelineLane(
            chainKey: 'dataset',
            isDutyFocus: dutySummary?.focusChainKey == 'dataset',
            title: '数据资产版本',
            description: '最近分析沉淀到资产链路的数据版本。',
            accent: AppColors.primary,
            icon: Icons.dataset_rounded,
            actionLabel: '打开数据分析',
            onTap: () => onNavigateToTab(2),
            items: summary.datasets
                .take(3)
                .map(
                  (item) => _TimelineItem(
                    version: item.createdAt == null
                        ? '--'
                        : DateFormat(
                            'MMdd-HHmm',
                          ).format(item.createdAt!.toLocal()),
                    headline: item.filename,
                    supporting:
                        'quality=${item.qualityScore?.toStringAsFixed(1) ?? '--'} · rows=${item.rows ?? '--'} · cols=${item.columns ?? '--'}',
                  ),
                )
                .toList(growable: false),
          ),
          _TimelineLane(
            chainKey: 'model',
            isDutyFocus: dutySummary?.focusChainKey == 'model',
            title: '模型版本轨迹',
            description: '最近训练产物的版本、目标列和来源数据。',
            accent: AppColors.cta,
            icon: Icons.model_training_rounded,
            actionLabel: '打开 AI Lab',
            onTap: () => onNavigateToTab(3),
            items: summary.models
                .take(3)
                .map(
                  (item) => _TimelineItem(
                    version: item.version,
                    headline:
                        '${(item.modelType ?? 'model').toUpperCase()} / ${item.targetColumn ?? '--'}',
                    supporting:
                        'path=${item.modelPath ?? '--'} · source=${item.storagePath ?? '--'}',
                  ),
                )
                .toList(growable: false),
          ),
          _TimelineLane(
            chainKey: 'knowledge',
            isDutyFocus: dutySummary?.focusChainKey == 'knowledge',
            title: '知识快照轨迹',
            description: '最近知识库构建的集合版本和来源文档。',
            accent: AppColors.success,
            icon: Icons.account_tree_rounded,
            actionLabel: '打开 AI Lab',
            onTap: () => onNavigateToTab(3),
            items: summary.knowledgeBases
                .take(3)
                .map(
                  (item) => _TimelineItem(
                    version: item.version,
                    headline: item.collection ?? 'default',
                    supporting:
                        'docs=${item.count ?? '--'} · ${item.reset == true ? 'reset' : 'incremental'} · source=${item.storagePath ?? '--'}',
                  ),
                )
                .toList(growable: false),
          ),
          _TimelineLane(
            chainKey: 'optimization',
            isDutyFocus: dutySummary?.focusChainKey == 'optimization',
            title: '优化快照轨迹',
            description: '最近后台优化登记到台账的版本和节省结果。',
            accent: AppColors.warning,
            icon: Icons.bolt_rounded,
            actionLabel: '打开能源优化',
            onTap: () => onNavigateToTab(1),
            items: summary.optimizations
                .take(3)
                .map(
                  (item) => _TimelineItem(
                    version: item.version,
                    headline: item.targetDate ?? '--',
                    supporting:
                        'soc=${_formatPercent(item.initialSoc)} · savings=${_formatNumber(item.savings, suffix: '元')}',
                  ),
                )
                .toList(growable: false),
          ),
        ]..sort((a, b) {
          final focusKey = dutySummary?.focusChainKey;
          final aFocused = a.chainKey == focusKey ? 1 : 0;
          final bFocused = b.chainKey == focusKey ? 1 : 0;
          if (aFocused != bFocused) {
            return bFocused.compareTo(aFocused);
          }
          return 0;
        });

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1080;
        if (compact) {
          return Column(
            children: [
              for (var i = 0; i < lanes.length; i++) ...[
                lanes[i],
                if (i < lanes.length - 1) const SizedBox(height: 12),
              ],
            ],
          );
        }

        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: lanes
              .map(
                (lane) => SizedBox(
                  width: (constraints.maxWidth - 12) / 2,
                  child: lane,
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}

class _TimelineLane extends StatelessWidget {
  const _TimelineLane({
    required this.chainKey,
    required this.isDutyFocus,
    required this.title,
    required this.description,
    required this.accent,
    required this.icon,
    required this.actionLabel,
    required this.onTap,
    required this.items,
  });

  final String chainKey;
  final bool isDutyFocus;
  final String title;
  final String description;
  final Color accent;
  final IconData icon;
  final String actionLabel;
  final VoidCallback onTap;
  final List<_TimelineItem> items;

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
                    if (isDutyFocus) ...[
                      const SizedBox(height: 8),
                      const WorkspaceStatusChip(
                        label: 'DUTY FOCUS',
                        icon: Icons.center_focus_strong_rounded,
                        foreground: AppColors.primary,
                        background: AppColors.infoLight,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (items.isEmpty)
            Text('暂无版本轨迹。', style: AppTextStyles.bodySmall)
          else
            ...items.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _TimelineTile(item: item, accent: accent),
              ),
            ),
          FilledButton.tonalIcon(
            onPressed: onTap,
            icon: const Icon(Icons.arrow_outward_rounded),
            label: Text(actionLabel),
          ),
        ],
      ),
    );
  }
}

class _TimelineItem {
  const _TimelineItem({
    required this.version,
    required this.headline,
    required this.supporting,
  });

  final String version;
  final String headline;
  final String supporting;
}

class _TimelineTile extends StatelessWidget {
  const _TimelineTile({required this.item, required this.accent});

  final _TimelineItem item;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            ),
            child: Text(
              'v${item.version}',
              style: AppTextStyles.labelMedium.copyWith(color: accent),
            ),
          ),
          const SizedBox(height: 10),
          Text(item.headline, style: AppTextStyles.labelLarge),
          const SizedBox(height: 6),
          Text(
            item.supporting,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

String _formatNumber(double? value, {required String suffix}) {
  if (value == null) {
    return '--';
  }
  return '${value.toStringAsFixed(1)}$suffix';
}

String _formatPercent(double? value) {
  if (value == null) {
    return '--';
  }
  return '${(value * 100).toStringAsFixed(0)}%';
}
