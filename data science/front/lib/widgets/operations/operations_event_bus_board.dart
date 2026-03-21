/// Unified event bus board for operations-level monitoring.
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../utils/asset_chain_context.dart';
import '../common/glass_card.dart';

class OperationsEventBusBoard extends StatelessWidget {
  const OperationsEventBusBoard({
    super.key,
    required this.summary,
    required this.onOpenChain,
  });

  final DashboardSummary summary;
  final ValueChanged<AssetChainSummary> onOpenChain;

  @override
  Widget build(BuildContext context) {
    final entries = _flattenEntries();
    final focusChains = [...summary.assetSummary.chainSummaries]
      ..sort((a, b) => b.priorityScore.compareTo(a.priorityScore));
    final incidents = entries
        .where((entry) => _sectionFor(entry) == _EventSection.incident)
        .length;
    final attention = entries
        .where((entry) => _sectionFor(entry) == _EventSection.attention)
        .length;
    final updates = entries
        .where((entry) => _sectionFor(entry) == _EventSection.updates)
        .length;

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('统一事件总线', style: AppTextStyles.h4),
          const SizedBox(height: 8),
          Text(
            '把链路版本、活跃作业、失败节点和最近审计动作收成值班视图。先看处置优先级，再看具体事件节点。',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _BusBadge(
                label: 'INCIDENT $incidents',
                foreground: incidents > 0 ? AppColors.error : AppColors.success,
                background: incidents > 0
                    ? AppColors.errorLight
                    : AppColors.successLight,
              ),
              _BusBadge(
                label: 'ATTENTION $attention',
                foreground: AppColors.warning,
                background: AppColors.warningLight,
              ),
              _BusBadge(
                label: 'UPDATES $updates',
                foreground: AppColors.primary,
                background: AppColors.infoLight,
              ),
            ],
          ),
          if (focusChains.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text('值班优先队列', style: AppTextStyles.labelLarge),
            const SizedBox(height: 10),
            Column(
              children: [
                for (var i = 0; i < focusChains.take(3).length; i++) ...[
                  _FocusQueueTile(
                    chain: focusChains[i],
                    onTap: () => onOpenChain(focusChains[i]),
                  ),
                  if (i < focusChains.take(3).length - 1)
                    const SizedBox(height: 10),
                ],
              ],
            ),
          ],
          const SizedBox(height: 16),
          if (entries.isEmpty)
            Text('暂无事件节点。', style: AppTextStyles.bodyMedium)
          else
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final section in _EventSection.values) ...[
                  _EventSectionGroup(
                    title: switch (section) {
                      _EventSection.incident => 'INCIDENT',
                      _EventSection.attention => 'ATTENTION',
                      _EventSection.updates => 'UPDATES',
                    },
                    entries: entries
                        .where((entry) => _sectionFor(entry) == section)
                        .toList(growable: false),
                    onOpenChain: onOpenChain,
                  ),
                  if (section != _EventSection.values.last)
                    const SizedBox(height: 16),
                ],
              ],
            ),
        ],
      ),
    );
  }

  List<_EventBusEntry> _flattenEntries() {
    final entries = <_EventBusEntry>[];
    for (final chain in summary.assetSummary.chainSummaries) {
      for (final node in chain.timeline) {
        entries.add(_EventBusEntry(chain: chain, node: node));
      }
    }
    entries.sort((a, b) {
      final sectionCompare = _sectionPriority(
        _sectionFor(b),
      ).compareTo(_sectionPriority(_sectionFor(a)));
      if (sectionCompare != 0) {
        return sectionCompare;
      }
      final chainCompare = b.chain.priorityScore.compareTo(
        a.chain.priorityScore,
      );
      if (chainCompare != 0) {
        return chainCompare;
      }
      return (b.node.timestamp ?? DateTime.fromMillisecondsSinceEpoch(0))
          .compareTo(
            a.node.timestamp ?? DateTime.fromMillisecondsSinceEpoch(0),
          );
    });
    return entries.take(12).toList(growable: false);
  }

  _EventSection _sectionFor(_EventBusEntry entry) {
    if (entry.node.level == 'error' || entry.chain.priorityScore >= 300) {
      return _EventSection.incident;
    }
    if (entry.chain.jobStatus == 'running' ||
        entry.chain.jobStatus == 'queued' ||
        entry.chain.priorityScore >= 160) {
      return _EventSection.attention;
    }
    return _EventSection.updates;
  }

  int _sectionPriority(_EventSection section) {
    switch (section) {
      case _EventSection.incident:
        return 3;
      case _EventSection.attention:
        return 2;
      case _EventSection.updates:
        return 1;
    }
  }
}

enum _EventSection { incident, attention, updates }

class _EventBusEntry {
  const _EventBusEntry({required this.chain, required this.node});

  final AssetChainSummary chain;
  final AssetChainNode node;
}

class _FocusQueueTile extends StatelessWidget {
  const _FocusQueueTile({required this.chain, required this.onTap});

  final AssetChainSummary chain;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final tone = _nodeColor(
      chain.status == 'incident'
          ? 'error'
          : chain.status == 'active'
          ? 'warning'
          : 'info',
    );
    final chainTone = _chainColor(chain.key);
    final cardLabel = buildDutyContextCardValue(chain.cardTargetLabel);
    final incidentLabel = buildDutyContextIncidentValue(chain.incidentTargetLabel);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: tone.withValues(alpha: 0.14)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 12,
            height: 12,
            margin: const EdgeInsets.only(top: 5),
            decoration: BoxDecoration(
              color: tone,
              borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _BusBadge(
                      label: chain.label,
                      foreground: chainTone,
                      background: chainTone.withValues(alpha: 0.12),
                    ),
                    _BusBadge(
                      label: chain.statusLabel,
                      foreground: tone,
                      background: tone.withValues(alpha: 0.12),
                    ),
                    if (cardLabel != null)
                      _BusBadge(
                        label: cardLabel,
                        foreground: chainTone,
                        background: chainTone.withValues(alpha: 0.1),
                      ),
                    _BusBadge(
                      label: chain.workspaceTargetLabel,
                      foreground: AppColors.textPrimary,
                      background: AppColors.surface,
                    ),
                    if (incidentLabel != null)
                      _BusBadge(
                        label: incidentLabel,
                        foreground: tone,
                        background: tone.withValues(alpha: 0.08),
                      ),
                    if (chain.isOverdue)
                      _BusBadge(
                        label: '超时 ${chain.overdueMinutes}m',
                        foreground: AppColors.error,
                        background: AppColors.errorLight,
                      )
                    else if (chain.escalationTier > 0)
                      _BusBadge(
                        label: 'SLA 关注',
                        foreground: AppColors.warning,
                        background: AppColors.warningLight,
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(cardLabel ?? chain.workspaceTargetLabel, style: AppTextStyles.labelLarge),
                const SizedBox(height: 4),
                Text(
                  buildChainWorkspaceSummary(chain),
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 8),
                _FocusSignal(chain: chain, accent: tone),
                const SizedBox(height: 6),
                Text(
                  '${chain.ownerLabel} · SLA ${chain.slaMinutes}min · ${chain.escalationStateLabel}',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                if (chain.slaDeadlineAt != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    'deadline ${_formatTime(chain.slaDeadlineAt)} · ${chain.escalationLabel}',
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          FilledButton.tonalIcon(
            onPressed: onTap,
            icon: const Icon(Icons.arrow_outward_rounded),
            label: Text(chain.actionLabel),
          ),
        ],
      ),
    );
  }
}

class _EventSectionGroup extends StatelessWidget {
  const _EventSectionGroup({
    required this.title,
    required this.entries,
    required this.onOpenChain,
  });

  final String title;
  final List<_EventBusEntry> entries;
  final ValueChanged<AssetChainSummary> onOpenChain;

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: AppTextStyles.labelMedium),
        const SizedBox(height: 10),
        Column(
          children: [
            for (var i = 0; i < entries.length; i++) ...[
              _EventBusTile(
                entry: entries[i],
                onTap: () => onOpenChain(entries[i].chain),
              ),
              if (i < entries.length - 1) const SizedBox(height: 12),
            ],
          ],
        ),
      ],
    );
  }
}

class _EventBusTile extends StatelessWidget {
  const _EventBusTile({required this.entry, required this.onTap});

  final _EventBusEntry entry;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final chainTone = _chainColor(entry.chain.key);
    final nodeTone = _nodeColor(entry.node.level);
    final cardLabel = buildDutyContextCardValue(entry.chain.cardTargetLabel);
    final incidentLabel = buildDutyContextIncidentValue(
      entry.chain.incidentTargetLabel,
    );
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: entry.chain.isOverdue || entry.chain.status != 'healthy'
            ? Color.alphaBlend(
                nodeTone.withValues(alpha: 0.05),
                AppColors.surfaceVariant,
              )
            : AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(
          color: chainTone.withValues(
            alpha: entry.chain.isOverdue || entry.chain.status != 'healthy'
                ? 0.22
                : 0.14,
          ),
          width: entry.chain.isOverdue ? 1.4 : 1,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 12,
            height: 12,
            margin: const EdgeInsets.only(top: 5),
            decoration: BoxDecoration(
              color: nodeTone,
              borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    _BusBadge(
                      label: entry.chain.label,
                      foreground: chainTone,
                      background: chainTone.withValues(alpha: 0.12),
                    ),
                    _BusBadge(
                      label: entry.node.badge,
                      foreground: nodeTone,
                      background: nodeTone.withValues(alpha: 0.12),
                    ),
                    _BusBadge(
                      label: entry.chain.statusLabel,
                      foreground: nodeTone,
                      background: nodeTone.withValues(alpha: 0.08),
                    ),
                    if (cardLabel != null)
                      _BusBadge(
                        label: cardLabel,
                        foreground: chainTone,
                        background: chainTone.withValues(alpha: 0.1),
                      ),
                    _BusBadge(
                      label: entry.chain.workspaceTargetLabel,
                      foreground: AppColors.textPrimary,
                      background: AppColors.surface,
                    ),
                    if (incidentLabel != null)
                      _BusBadge(
                        label: incidentLabel,
                        foreground: nodeTone,
                        background: nodeTone.withValues(alpha: 0.08),
                      ),
                    if (entry.chain.isOverdue)
                      _BusBadge(
                        label: '超时 ${entry.chain.overdueMinutes}m',
                        foreground: AppColors.error,
                        background: AppColors.errorLight,
                      )
                    else if (entry.chain.escalationTier > 0)
                      _BusBadge(
                        label: 'SLA 关注',
                        foreground: AppColors.warning,
                        background: AppColors.warningLight,
                      ),
                    if (entry.chain.jobStatus == 'running' ||
                        entry.chain.jobStatus == 'queued')
                      _BusBadge(
                        label:
                            '${entry.chain.jobStatus.toUpperCase()} ${entry.chain.jobProgress}%',
                        foreground: AppColors.cta,
                        background: const Color(0xFFFFEDD5),
                      ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(entry.node.title, style: AppTextStyles.labelLarge),
                const SizedBox(height: 4),
                Text(
                  buildChainWorkspaceSummary(
                    entry.chain,
                    includeWorkspaceLabel: true,
                  ),
                  style: AppTextStyles.bodySmall.copyWith(color: chainTone),
                ),
                const SizedBox(height: 8),
                _FocusSignal(chain: entry.chain, accent: nodeTone),
                const SizedBox(height: 4),
                Text(
                  _eventNodeSummary(entry),
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                _formatTime(entry.node.timestamp),
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              if (entry.chain.slaDeadlineAt != null) ...[
                const SizedBox(height: 6),
                Text(
                  '截止 ${_formatTime(entry.chain.slaDeadlineAt)}',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: entry.chain.isOverdue
                        ? AppColors.error
                        : AppColors.textSecondary,
                  ),
                ),
              ],
              const SizedBox(height: 10),
              FilledButton.tonalIcon(
                onPressed: onTap,
                icon: const Icon(Icons.arrow_outward_rounded),
                label: Text(entry.chain.actionLabel),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _FocusSignal extends StatelessWidget {
  const _FocusSignal({required this.chain, required this.accent});

  final AssetChainSummary chain;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final incidentLabel = buildDutyContextIncidentValue(chain.incidentTargetLabel);
    final watchSummary = sanitizeWorkspaceSummaryText(
      chain.incidentBrief,
      duplicatedLabels: [
        chain.workspaceTargetLabel,
        chain.cardTargetLabel,
        incidentLabel,
      ],
    );
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          accent.withValues(alpha: 0.05),
          AppColors.surface,
        ),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            incidentLabel == null ? '当前关注' : '当前关注 · $incidentLabel',
            style: AppTextStyles.labelMedium.copyWith(color: accent),
          ),
          const SizedBox(height: 4),
          Text(
            watchSummary ?? '--',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

String _eventNodeSummary(_EventBusEntry entry) {
  final segments = <String>[
    if (entry.node.phaseLabel != '--') entry.node.phaseLabel,
    if (entry.node.sourceLabel != '--') entry.node.sourceLabel,
    if (entry.node.versionTag != '--') 'v${entry.node.versionTag}',
    entry.node.detail,
  ];
  return segments.join(' · ');
}

class _BusBadge extends StatelessWidget {
  const _BusBadge({
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

String _formatTime(DateTime? value) {
  if (value == null) {
    return '--';
  }
  return DateFormat('MM-dd HH:mm').format(value.toLocal());
}

Color _chainColor(String key) {
  switch (key) {
    case 'dataset':
      return AppColors.primary;
    case 'model':
      return AppColors.cta;
    case 'knowledge':
      return AppColors.success;
    case 'optimization':
      return AppColors.warning;
    default:
      return AppColors.textSecondary;
  }
}

Color _nodeColor(String level) {
  switch (level) {
    case 'error':
      return AppColors.error;
    case 'warning':
      return AppColors.warning;
    default:
      return AppColors.primary;
  }
}
