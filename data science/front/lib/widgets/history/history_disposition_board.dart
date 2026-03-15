/// Grouped disposition board for history and audit workflows.
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../models/history_record.dart';
import '../../models/job_record.dart';
import '../../utils/asset_chain_context.dart';
import '../common/glass_card.dart';
import '../operations/duty_section_block.dart';
import '../operations/incident_card_header.dart';
import '../operations/workspace_action_lane.dart';

class HistoryDispositionBoard extends StatelessWidget {
  const HistoryDispositionBoard({
    super.key,
    required this.assetSummary,
    this.dutySummary,
    required this.jobs,
    required this.records,
    required this.onGovernanceAction,
    required this.onFailureAction,
    required this.onFilterFailures,
    required this.onReplayAction,
    this.trailing,
  });

  final AssetSummary assetSummary;
  final DutySummary? dutySummary;
  final List<JobRecord> jobs;
  final List<HistoryRecord> records;
  final ValueChanged<AssetGovernanceItem> onGovernanceAction;
  final ValueChanged<AssetFailureChain> onFailureAction;
  final ValueChanged<String> onFilterFailures;
  final ValueChanged<String> onReplayAction;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final groups = _buildGroups();
    return DutySectionBlock(
      title: '分组处置流',
      subtitle: '把失败链路、资产风险、快速回放和最近链路节点按资产类型收成统一处置面，不再在审计页里来回切换重复入口。',
      trailing: trailing,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 1180;
          if (compact) {
            return Column(
              children: [
                for (var i = 0; i < groups.length; i++) ...[
                  _DispositionCard(
                    group: groups[i],
                    isDutyFocus: isDutyFocusChain(groups[i].chain, dutySummary),
                    onGovernanceAction: () =>
                        onGovernanceAction(groups[i].governance),
                    onFailureAction: groups[i].failure == null
                        ? null
                        : () => onFailureAction(groups[i].failure!),
                    onFilterFailures: groups[i].failure == null
                        ? null
                        : () => onFilterFailures(groups[i].key),
                    onReplayAction: groups[i].replayCount == 0
                        ? null
                        : () => onReplayAction(groups[i].key),
                  ),
                  if (i < groups.length - 1) const SizedBox(height: 12),
                ],
              ],
            );
          }

          return Wrap(
            spacing: 12,
            runSpacing: 12,
            children: groups
                .map(
                  (group) => SizedBox(
                    width: (constraints.maxWidth - 12) / 2,
                    child: _DispositionCard(
                      group: group,
                      isDutyFocus: isDutyFocusChain(group.chain, dutySummary),
                      onGovernanceAction: () =>
                          onGovernanceAction(group.governance),
                      onFailureAction: group.failure == null
                          ? null
                          : () => onFailureAction(group.failure!),
                      onFilterFailures: group.failure == null
                          ? null
                          : () => onFilterFailures(group.key),
                      onReplayAction: group.replayCount == 0
                          ? null
                          : () => onReplayAction(group.key),
                    ),
                  ),
                )
                .toList(growable: false),
          );
        },
      ),
    );
  }

  List<_DispositionGroup> _buildGroups() {
    const configs = [
      _DispositionConfig(
        key: 'dataset',
        label: '数据资产',
        accent: AppColors.primary,
        icon: Icons.dataset_rounded,
      ),
      _DispositionConfig(
        key: 'model',
        label: '模型资产',
        accent: AppColors.cta,
        icon: Icons.model_training_rounded,
      ),
      _DispositionConfig(
        key: 'knowledge',
        label: '知识快照',
        accent: AppColors.success,
        icon: Icons.account_tree_rounded,
      ),
      _DispositionConfig(
        key: 'optimization',
        label: '优化快照',
        accent: AppColors.warning,
        icon: Icons.bolt_rounded,
      ),
    ];

    final groups = configs
        .map((config) {
          final governance = assetSummary.governance.firstWhere(
            (item) => item.key == config.key,
          );
          final failure = assetSummary.failureChains
              .cast<AssetFailureChain?>()
              .firstWhere(
                (item) => item?.key == config.key,
                orElse: () => null,
              );
          final replay = _replaySnapshot(config.key);
          final chain = assetSummary.chainSummaries
              .cast<AssetChainSummary?>()
              .firstWhere(
                (item) => item?.key == config.key,
                orElse: () => null,
              );
          return _DispositionGroup(
            key: config.key,
            label: config.label,
            accent: config.accent,
            icon: config.icon,
            chain: chain,
            governance: governance,
            failure: failure,
            replayCount: replay.$1,
            replayLabel: replay.$2,
          );
        })
        .toList(growable: false);
    groups.sort(
      (a, b) => compareChainsByDutyFocus(a.chain, b.chain, dutySummary),
    );
    return groups;
  }

  (int, String) _replaySnapshot(String key) {
    switch (key) {
      case 'dataset':
        final replayable = records
            .where(
              (record) =>
                  record.summary != null ||
                  (record.storageUrl?.isNotEmpty ?? false),
            )
            .toList(growable: false);
        return (
          replayable.length,
          replayable.isEmpty ? '--' : replayable.first.filename,
        );
      case 'model':
        final replayable = jobs
            .where(
              (job) =>
                  job.type == 'ml_train' &&
                  job.status == 'succeeded' &&
                  (job.result['model_path']?.toString().isNotEmpty ?? false),
            )
            .toList(growable: false);
        return (
          replayable.length,
          replayable.isEmpty
              ? '--'
              : '${(replayable.first.result['model_type'] ?? replayable.first.input['model_type'] ?? '--').toString()} / ${(replayable.first.result['target_column'] ?? replayable.first.input['target_column'] ?? '--').toString()}',
        );
      case 'knowledge':
        final replayable = jobs
            .where(
              (job) =>
                  job.type == 'rag_ingest' &&
                  job.status == 'succeeded' &&
                  ((job.result['collection'] ?? job.input['collection_name'])
                          ?.toString()
                          .isNotEmpty ??
                      false),
            )
            .toList(growable: false);
        return (
          replayable.length,
          replayable.isEmpty
              ? '--'
              : (replayable.first.result['collection'] ??
                        replayable.first.input['collection_name'] ??
                        '--')
                    .toString(),
        );
      case 'optimization':
        final replayable = jobs
            .where(
              (job) =>
                  job.type == 'optimization' &&
                  job.status == 'succeeded' &&
                  job.result.isNotEmpty,
            )
            .toList(growable: false);
        return (
          replayable.length,
          replayable.isEmpty
              ? '--'
              : (replayable.first.input['target_date'] ?? '--').toString(),
        );
      default:
        return (0, '--');
    }
  }
}

class _DispositionConfig {
  const _DispositionConfig({
    required this.key,
    required this.label,
    required this.accent,
    required this.icon,
  });

  final String key;
  final String label;
  final Color accent;
  final IconData icon;
}

class _DispositionGroup {
  const _DispositionGroup({
    required this.key,
    required this.label,
    required this.accent,
    required this.icon,
    required this.chain,
    required this.governance,
    required this.failure,
    required this.replayCount,
    required this.replayLabel,
  });

  final String key;
  final String label;
  final Color accent;
  final IconData icon;
  final AssetChainSummary? chain;
  final AssetGovernanceItem governance;
  final AssetFailureChain? failure;
  final int replayCount;
  final String replayLabel;
}

class _DispositionCard extends StatelessWidget {
  const _DispositionCard({
    required this.group,
    required this.isDutyFocus,
    required this.onGovernanceAction,
    this.onFailureAction,
    this.onFilterFailures,
    this.onReplayAction,
  });

  final _DispositionGroup group;
  final bool isDutyFocus;
  final VoidCallback onGovernanceAction;
  final VoidCallback? onFailureAction;
  final VoidCallback? onFilterFailures;
  final VoidCallback? onReplayAction;

  @override
  Widget build(BuildContext context) {
    final tone = _DispositionTone.fromRisk(
      group.failure != null ? 'action' : group.governance.riskLevel,
      group.accent,
    );
    final focusArea = _focusAreaForTarget(group.chain);

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IncidentCardHeader(
            accent: tone.foreground,
            icon: group.icon,
            title: group.label,
            subtitle:
                'latest v${group.governance.latestVersion} · ${group.governance.latestLabel}',
            supportingText: group.chain == null
                ? '${group.governance.ownerLabel} · SLA ${group.governance.slaMinutes}min · ${group.governance.escalationLabel}'
                : '${group.chain!.statusLabel} · ${group.chain!.workspaceTargetLabel}',
            supportingColor: group.chain == null
                ? AppColors.textSecondary
                : group.accent,
            trailing: WorkspaceStatusChip(
              label: isDutyFocus
                  ? 'DUTY FOCUS'
                  : group.failure != null
                  ? 'FAIL'
                  : group.governance.riskLevel.toUpperCase(),
              icon: group.failure != null
                  ? Icons.error_outline_rounded
                  : isDutyFocus
                  ? Icons.center_focus_strong_rounded
                  : group.icon,
              foreground: tone.foreground,
              background: tone.background,
            ),
            workspaceLabel:
                group.chain?.workspaceTargetLabel ??
                group.governance.workspaceTargetLabel,
            cardLabel: group.chain?.cardTargetLabel,
            incidentLabel: group.chain?.incidentTargetLabel,
            summary:
                group.chain?.workspaceBrief ?? group.governance.workspaceBrief,
          ),
          const SizedBox(height: 14),
          _DispositionRow(
            label: '风险建议',
            value: group.governance.recommendedAction,
            highlighted: focusArea == _DispositionFocusArea.governance,
            accent: tone.foreground,
          ),
          _DispositionRow(
            label: '当前焦点',
            value: group.chain == null ? '当前无链路焦点' : group.chain!.incidentBrief,
            highlighted: focusArea == _DispositionFocusArea.focus,
            accent: group.accent,
          ),
          _DispositionRow(
            label: '目标落点',
            value: group.chain == null
                ? '当前无目标落点'
                : '${group.chain!.workspaceTargetLabel} · ${group.chain!.cardTargetLabel} · ${group.chain!.incidentTargetLabel}',
            highlighted: group.chain != null,
            accent: group.accent,
          ),
          _DispositionRow(
            label: '值班责任',
            value: group.chain == null
                ? '${group.governance.ownerLabel} · SLA ${group.governance.slaMinutes}min · ${group.governance.escalationLabel}'
                : '${group.chain!.ownerLabel} · SLA ${group.chain!.slaMinutes}min · ${group.chain!.escalationLabel}',
          ),
          _DispositionRow(
            label: '响应时限',
            value: group.chain == null
                ? '当前无 SLA 追踪'
                : '${group.chain!.escalationStateLabel} · ${group.chain!.isOverdue ? 'overdue ${group.chain!.overdueMinutes}m' : 'elapsed ${group.chain!.elapsedMinutes}m'}${group.chain!.slaDeadlineAt == null ? '' : ' · due ${_formatTime(group.chain!.slaDeadlineAt)}'}',
            highlighted: focusArea == _DispositionFocusArea.sla,
            accent: group.chain?.isOverdue ?? false
                ? AppColors.error
                : group.accent,
          ),
          _DispositionRow(
            label: '版本血缘',
            value: group.governance.lineageSummary,
          ),
          _DispositionRow(
            label: '活跃作业',
            value: group.chain == null || group.chain!.jobStatus == '--'
                ? '当前无活跃作业'
                : '${group.chain!.jobStatus} · ${group.chain!.jobPhase} · ${group.chain!.jobProgress}%',
            highlighted: focusArea == _DispositionFocusArea.job,
            accent: AppColors.warning,
          ),
          _DispositionRow(
            label: '最近活动',
            value: group.chain == null || group.chain!.activityTitle == '--'
                ? '暂无审计活动'
                : '${group.chain!.activityTitle} · ${group.chain!.activitySource}',
          ),
          _DispositionRow(
            label: '回放库存',
            value: group.chain == null
                ? '${group.replayCount} · ${group.replayLabel}'
                : '${group.replayCount} · ${group.replayLabel} · ${group.chain!.workspaceBrief}',
            highlighted: focusArea == _DispositionFocusArea.replay,
            accent: AppColors.primary,
          ),
          _DispositionRow(
            label: '失败链路',
            value: group.failure == null
                ? (group.governance.failureSummary == '--'
                      ? '当前无最新失败来源'
                      : group.governance.failureSummary)
                : '${group.failure!.sourceSummary} · ${group.failure!.latestPhase}',
            highlighted: focusArea == _DispositionFocusArea.failure,
            accent: AppColors.error,
          ),
          if ((group.chain?.timeline.isNotEmpty ?? false)) ...[
            const SizedBox(height: 10),
            _DispositionTimeline(nodes: group.chain!.timeline),
          ],
          const SizedBox(height: 14),
          WorkspaceInlineActionBar(
            recommendedActionKey: _recommendedDispositionActionKey(group),
            actions: [
              if (onFilterFailures != null)
                WorkspaceActionLaneAction(
                  label: '仅看失败',
                  icon: Icons.filter_alt_rounded,
                  semanticKey: 'filter_failures',
                  onTap: onFilterFailures,
                ),
              if (onReplayAction != null)
                WorkspaceActionLaneAction(
                  label: '回放最新',
                  icon: Icons.replay_circle_filled_rounded,
                  semanticKey: 'replay_latest',
                  onTap: onReplayAction,
                ),
              WorkspaceActionLaneAction(
                label: onFailureAction == null
                    ? group.governance.actionLabel
                    : group.failure!.actionLabel,
                icon: onFailureAction == null
                    ? Icons.arrow_outward_rounded
                    : Icons.build_circle_outlined,
                semanticKey: onFailureAction == null
                    ? 'governance_action'
                    : 'failure_action',
                onTap: onFailureAction ?? onGovernanceAction,
                tone: WorkspaceActionLaneTone.tonal,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

String? _recommendedDispositionActionKey(_DispositionGroup group) {
  final focusArea = _focusAreaForTarget(group.chain);
  switch (focusArea) {
    case _DispositionFocusArea.failure:
      return group.failure == null ? 'filter_failures' : 'failure_action';
    case _DispositionFocusArea.replay:
      return group.replayCount > 0 ? 'replay_latest' : 'governance_action';
    case _DispositionFocusArea.job:
    case _DispositionFocusArea.sla:
    case _DispositionFocusArea.focus:
    case _DispositionFocusArea.governance:
      return group.failure != null ? 'failure_action' : 'governance_action';
  }
}

class _DispositionRow extends StatelessWidget {
  const _DispositionRow({
    required this.label,
    required this.value,
    this.highlighted = false,
    this.accent,
  });

  final String label;
  final String value;
  final bool highlighted;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    final highlightColor = accent ?? AppColors.primary;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 10),
      padding: highlighted
          ? const EdgeInsets.symmetric(horizontal: 10, vertical: 8)
          : EdgeInsets.zero,
      decoration: highlighted
          ? BoxDecoration(
              color: highlightColor.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              border: Border.all(color: highlightColor.withValues(alpha: 0.18)),
            )
          : null,
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
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.bodyMedium.copyWith(
                color: highlighted ? AppColors.textPrimary : null,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DispositionTimeline extends StatelessWidget {
  const _DispositionTimeline({required this.nodes});

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
            '最近链路节点',
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          for (var i = 0; i < nodes.length; i++) ...[
            _DispositionNode(node: nodes[i]),
            if (i < nodes.length - 1) const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _DispositionNode extends StatelessWidget {
  const _DispositionNode({required this.node});

  final AssetChainNode node;

  @override
  Widget build(BuildContext context) {
    final tone = _nodeColor(node.level);
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
                '${node.badge} · ${node.phaseLabel} · ${node.detail}',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DispositionTone {
  const _DispositionTone({required this.foreground, required this.background});

  final Color foreground;
  final Color background;

  factory _DispositionTone.fromRisk(String riskLevel, Color accent) {
    switch (riskLevel) {
      case 'action':
        return const _DispositionTone(
          foreground: AppColors.error,
          background: AppColors.errorLight,
        );
      case 'watch':
        return const _DispositionTone(
          foreground: AppColors.warning,
          background: AppColors.warningLight,
        );
      default:
        return _DispositionTone(
          foreground: accent,
          background: accent.withValues(alpha: 0.12),
        );
    }
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

String _formatTime(DateTime? value) {
  if (value == null) {
    return '--';
  }
  return DateFormat('MM-dd HH:mm').format(value.toLocal());
}

_DispositionFocusArea _focusAreaForTarget(AssetChainSummary? chain) {
  switch (chain?.dispositionTarget) {
    case 'governance':
      return _DispositionFocusArea.governance;
    case 'job':
      return _DispositionFocusArea.job;
    case 'replay':
      return _DispositionFocusArea.replay;
    case 'sla':
      return _DispositionFocusArea.sla;
    case 'failure':
      return _DispositionFocusArea.failure;
    case 'focus':
    default:
      return _DispositionFocusArea.focus;
  }
}

enum _DispositionFocusArea { governance, focus, sla, replay, failure, job }
