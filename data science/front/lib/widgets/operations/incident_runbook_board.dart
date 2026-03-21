library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../utils/asset_chain_context.dart';
import '../common/glass_card.dart';
import 'duty_section_block.dart';
import 'incident_card_header.dart';
import 'workspace_action_lane.dart';

class IncidentRunbookBoard extends StatelessWidget {
  const IncidentRunbookBoard({
    super.key,
    required this.summary,
    required this.onOpenChain,
    this.title = '处置清单',
    this.description = '把最需要处置的链路压成统一清单，概览页和值班审计页都消费同一份后端处置说明。',
    this.trailing,
    this.dutySummary,
  });

  final AssetSummary summary;
  final ValueChanged<AssetChainSummary> onOpenChain;
  final String title;
  final String description;
  final Widget? trailing;
  final DutySummary? dutySummary;

  @override
  Widget build(BuildContext context) {
    final chains = [...summary.chainSummaries]
      ..sort((a, b) => compareChainsByDutyFocus(a, b, dutySummary));
    final items = chains
        .where((chain) => chain.runbookSteps.isNotEmpty)
        .take(3)
        .toList(growable: false);
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    return DutySectionBlock(
      title: title,
      subtitle: description,
      trailing: trailing,
      child: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 1180) {
            return Column(
              children: [
                for (var i = 0; i < items.length; i++) ...[
                  _RunbookCard(
                    chain: items[i],
                    isDutyFocus: isDutyFocusChain(items[i], dutySummary),
                    onOpen: () => onOpenChain(items[i]),
                  ),
                  if (i < items.length - 1) const SizedBox(height: 12),
                ],
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < items.length; i++) ...[
                Expanded(
                  child: _RunbookCard(
                    chain: items[i],
                    isDutyFocus: isDutyFocusChain(items[i], dutySummary),
                    onOpen: () => onOpenChain(items[i]),
                  ),
                ),
                if (i < items.length - 1) const SizedBox(width: 12),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _RunbookCard extends StatelessWidget {
  const _RunbookCard({
    required this.chain,
    required this.isDutyFocus,
    required this.onOpen,
  });

  final AssetChainSummary chain;
  final bool isDutyFocus;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(chain);
    final accent = _chainColor(chain.key);

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _RunbookBadge(
                label: chain.label,
                foreground: accent,
                background: accent.withValues(alpha: 0.12),
              ),
              _RunbookBadge(
                label: chain.statusLabel,
                foreground: tone,
                background: tone.withValues(alpha: 0.12),
              ),
              _RunbookBadge(
                label: chain.workspaceTargetLabel,
                foreground: AppColors.textPrimary,
                background: AppColors.surfaceVariant,
              ),
              if (isDutyFocus)
                _RunbookBadge(
                  label: '值班焦点',
                  foreground: AppColors.primary,
                  background: AppColors.infoLight,
                ),
              if (chain.isOverdue)
                _RunbookBadge(
                  label: '超时 ${chain.overdueMinutes}m',
                  foreground: AppColors.error,
                  background: AppColors.errorLight,
                )
              else if (chain.escalationTier > 0)
                _RunbookBadge(
                  label: 'SLA 关注',
                  foreground: AppColors.warning,
                  background: AppColors.warningLight,
                ),
            ],
          ),
          const SizedBox(height: 12),
          IncidentCardHeader(
            accent: accent,
            icon: Icons.rule_folder_rounded,
            title: chain.runbookTitle,
            subtitle:
                '${chain.ownerLabel} · SLA ${chain.slaMinutes}min · ${chain.escalationStateLabel}',
            supportingText: chain.slaDeadlineAt == null
                ? null
                : 'deadline ${DateFormat('MM-dd HH:mm').format(chain.slaDeadlineAt!.toLocal())} · ${chain.escalationLabel}',
            supportingColor: chain.isOverdue
                ? AppColors.error
                : AppColors.textSecondary,
            workspaceLabel: chain.workspaceTargetLabel,
            cardLabel: chain.cardTargetLabel,
            incidentLabel: chain.incidentTargetLabel,
            summary: buildChainWorkspaceSummary(chain),
          ),
          const SizedBox(height: 12),
          for (var i = 0; i < chain.runbookSteps.length; i++) ...[
            _RunbookStep(index: i + 1, text: chain.runbookSteps[i], tone: tone),
            if (i < chain.runbookSteps.length - 1) const SizedBox(height: 10),
          ],
          const SizedBox(height: 14),
          WorkspaceInlineActionBar(
            actions: [
              WorkspaceActionLaneAction(
                label: chain.actionLabel,
                icon: Icons.arrow_outward_rounded,
                onTap: onOpen,
                tone: WorkspaceActionLaneTone.tonal,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RunbookStep extends StatelessWidget {
  const _RunbookStep({
    required this.index,
    required this.text,
    required this.tone,
  });

  final int index;
  final String text;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 24,
          height: 24,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: tone.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
          ),
          child: Text(
            '$index',
            style: AppTextStyles.labelMedium.copyWith(color: tone),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: AppTextStyles.bodyMedium)),
      ],
    );
  }
}

class _RunbookBadge extends StatelessWidget {
  const _RunbookBadge({
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

Color _toneFor(AssetChainSummary chain) {
  if (chain.isOverdue || chain.status == 'incident') {
    return AppColors.error;
  }
  if (chain.escalationTier > 0 || chain.status == 'active') {
    return AppColors.warning;
  }
  return AppColors.primary;
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
