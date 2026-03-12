/// Unified audit event stream for jobs and audit activities.
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../models/job_record.dart';
import '../common/glass_card.dart';
import '../operations/section_intro.dart';

class AuditEventStream extends StatelessWidget {
  const AuditEventStream({
    super.key,
    required this.jobs,
    required this.activity,
    this.assetSummary,
    required this.onOpenChain,
    this.onOpenChainSummary,
    required this.onFilterFailures,
  });

  final List<JobRecord> jobs;
  final List<AuditActivity> activity;
  final AssetSummary? assetSummary;
  final ValueChanged<String> onOpenChain;
  final ValueChanged<AssetChainSummary>? onOpenChainSummary;
  final ValueChanged<String> onFilterFailures;

  @override
  Widget build(BuildContext context) {
    final entries = _buildEntries();
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionIntro(
            title: '统一审计事件流',
            subtitle: '把任务执行和审计活动合并到同一条时间线里，减少在审计页里并行维护两套列表。',
          ),
          const SizedBox(height: 14),
          if (entries.isEmpty)
            Text('当前过滤条件下暂无事件。', style: AppTextStyles.bodyMedium)
          else
            Column(
              children: [
                for (var i = 0; i < entries.length; i++) ...[
                  _AuditStreamTile(
                    entry: entries[i],
                    onOpen: () {
                      final chain = entries[i].chain;
                      if (chain != null && onOpenChainSummary != null) {
                        onOpenChainSummary!(chain);
                        return;
                      }
                      onOpenChain(entries[i].key);
                    },
                    onFilterFailure: entries[i].isFailure
                        ? () => onFilterFailures(entries[i].key)
                        : null,
                  ),
                  if (i < entries.length - 1) const SizedBox(height: 12),
                ],
              ],
            ),
        ],
      ),
    );
  }

  List<_AuditStreamEntry> _buildEntries() {
    final chainByKey = {
      for (final chain
          in assetSummary?.chainSummaries ?? const <AssetChainSummary>[])
        chain.key: chain,
    };
    final entries = <_AuditStreamEntry>[
      ...jobs.map(
        (job) => _AuditStreamEntry(
          key: _jobKey(job.type),
          lane: job.displayTitle,
          badge: job.status.toUpperCase(),
          title: job.statusMessage ?? job.displayTitle,
          detail:
              '${job.latestEvent?.phase ?? job.status} · ${job.progress}% · ${job.jobId.substring(0, 8)}',
          timestamp:
              job.latestEvent?.timestamp ?? job.submittedAt ?? job.completedAt,
          isFailure: job.status == 'failed',
          level: job.status == 'failed'
              ? 'error'
              : (job.isRunning ? 'warning' : 'info'),
          chain: chainByKey[_jobKey(job.type)],
        ),
      ),
      ...activity.map(
        (item) => _AuditStreamEntry(
          key: _activityKey(item),
          lane: item.source,
          badge: item.status.toUpperCase(),
          title: item.title,
          detail: '${item.resourceType ?? '--'} · ${item.resourceId ?? '--'}',
          timestamp: item.createdAt,
          isFailure: item.status == 'failed',
          level: item.severity == 'error'
              ? 'error'
              : (item.severity == 'warning' ? 'warning' : 'info'),
          chain: chainByKey[_activityKey(item)],
        ),
      ),
    ];

    entries.sort((a, b) {
      final priorityCompare = _entryPriority(b).compareTo(_entryPriority(a));
      if (priorityCompare != 0) {
        return priorityCompare;
      }
      return (b.timestamp ?? DateTime.fromMillisecondsSinceEpoch(0)).compareTo(
        a.timestamp ?? DateTime.fromMillisecondsSinceEpoch(0),
      );
    });
    return entries.take(12).toList(growable: false);
  }

  String _jobKey(String type) {
    switch (type) {
      case 'analysis':
        return 'dataset';
      case 'ml_train':
        return 'model';
      case 'rag_ingest':
        return 'knowledge';
      case 'optimization':
        return 'optimization';
      default:
        return 'dataset';
    }
  }

  String _activityKey(AuditActivity item) {
    final source = item.source.toLowerCase();
    if (source == 'analysis' || source == 'history') {
      return 'dataset';
    }
    if (source == 'ml_train') {
      return 'model';
    }
    if (source == 'rag_ingest' || source == 'rag') {
      return 'knowledge';
    }
    if (source == 'optimization') {
      return 'optimization';
    }
    return 'dataset';
  }
}

class _AuditStreamEntry {
  const _AuditStreamEntry({
    required this.key,
    required this.lane,
    required this.badge,
    required this.title,
    required this.detail,
    required this.timestamp,
    required this.isFailure,
    required this.level,
    this.chain,
  });

  final String key;
  final String lane;
  final String badge;
  final String title;
  final String detail;
  final DateTime? timestamp;
  final bool isFailure;
  final String level;
  final AssetChainSummary? chain;
}

class _AuditStreamTile extends StatelessWidget {
  const _AuditStreamTile({
    required this.entry,
    required this.onOpen,
    this.onFilterFailure,
  });

  final _AuditStreamEntry entry;
  final VoidCallback onOpen;
  final VoidCallback? onFilterFailure;

  @override
  Widget build(BuildContext context) {
    final tone = _eventTone(entry);
    final highlighted =
        entry.chain?.isOverdue == true ||
        entry.chain?.status == 'incident' ||
        entry.chain?.status == 'active';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: highlighted
            ? Color.alphaBlend(
                tone.withValues(alpha: 0.06),
                AppColors.surfaceVariant,
              )
            : AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(
          color: tone.withValues(alpha: highlighted ? 0.24 : 0.14),
          width: entry.chain?.isOverdue == true ? 1.4 : 1,
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
                    _AuditStreamBadge(
                      label: entry.lane,
                      foreground: tone,
                      background: tone.withValues(alpha: 0.12),
                    ),
                    _AuditStreamBadge(
                      label: entry.badge,
                      foreground: tone,
                      background: tone.withValues(alpha: 0.12),
                    ),
                    if (entry.chain != null)
                      _AuditStreamBadge(
                        label: entry.chain!.statusLabel,
                        foreground: tone,
                        background: tone.withValues(alpha: 0.12),
                      ),
                    if (entry.chain != null)
                      _AuditStreamBadge(
                        label: entry.chain!.workspaceTargetLabel,
                        foreground: tone,
                        background: tone.withValues(alpha: 0.08),
                      ),
                    if (entry.chain != null)
                      _AuditStreamBadge(
                        label: entry.chain!.incidentTargetLabel,
                        foreground: tone,
                        background: tone.withValues(alpha: 0.08),
                      ),
                    if (entry.chain != null)
                      _AuditStreamBadge(
                        label: entry.chain!.cardTargetLabel,
                        foreground: tone,
                        background: tone.withValues(alpha: 0.12),
                      ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(entry.title, style: AppTextStyles.labelLarge),
                if (entry.chain != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    '${entry.chain!.workspaceTargetLabel} · ${entry.chain!.workspaceBrief}',
                    style: AppTextStyles.bodySmall.copyWith(color: tone),
                  ),
                  const SizedBox(height: 8),
                  _AuditSignal(chain: entry.chain!, tone: tone),
                ],
                const SizedBox(height: 4),
                Text(
                  entry.detail,
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
                _formatTime(entry.timestamp),
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.end,
                children: [
                  if (onFilterFailure != null)
                    OutlinedButton.icon(
                      onPressed: onFilterFailure,
                      icon: const Icon(Icons.filter_alt_rounded),
                      label: const Text('仅看失败'),
                    ),
                  FilledButton.tonalIcon(
                    onPressed: onOpen,
                    icon: const Icon(Icons.arrow_outward_rounded),
                    label: Text(entry.chain?.actionLabel ?? '打开工作台'),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AuditSignal extends StatelessWidget {
  const _AuditSignal({required this.chain, required this.tone});

  final AssetChainSummary chain;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          tone.withValues(alpha: 0.05),
          AppColors.surface,
        ),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: tone.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Current watch · ${chain.incidentTargetLabel}',
            style: AppTextStyles.labelMedium.copyWith(color: tone),
          ),
          const SizedBox(height: 4),
          Text(
            chain.incidentBrief,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

int _entryPriority(_AuditStreamEntry entry) {
  if (entry.chain != null) {
    return entry.chain!.priorityScore;
  }
  if (entry.isFailure) {
    return 300;
  }
  if (entry.level == 'warning') {
    return 180;
  }
  return 80;
}

Color _eventTone(_AuditStreamEntry entry) {
  final chain = entry.chain;
  if (chain != null) {
    if (chain.isOverdue || chain.status == 'incident') {
      return AppColors.error;
    }
    if (chain.status == 'active' || chain.escalationTier > 0) {
      return AppColors.warning;
    }
  }
  return _tone(entry.level);
}

class _AuditStreamBadge extends StatelessWidget {
  const _AuditStreamBadge({
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

Color _tone(String level) {
  switch (level) {
    case 'error':
      return AppColors.error;
    case 'warning':
      return AppColors.warning;
    default:
      return AppColors.primary;
  }
}
