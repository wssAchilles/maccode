library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';
import 'workbench_command_strip.dart';

class WorkbenchRunbookPanel extends StatelessWidget {
  const WorkbenchRunbookPanel({
    super.key,
    required this.chain,
    required this.description,
    required this.actions,
  });

  final AssetChainSummary? chain;
  final String description;
  final List<WorkbenchCommandAction> actions;

  @override
  Widget build(BuildContext context) {
    final activeChain = chain;
    if (activeChain == null) {
      return const SizedBox.shrink();
    }

    final tone = _toneFor(activeChain);
    final accent = _chainColor(activeChain.key);

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _RunbookBadge(
                label: activeChain.label,
                foreground: accent,
                background: accent.withValues(alpha: 0.12),
              ),
              _RunbookBadge(
                label: activeChain.statusLabel,
                foreground: tone,
                background: tone.withValues(alpha: 0.12),
              ),
              _RunbookBadge(
                label: activeChain.workspaceTargetLabel,
                foreground: accent,
                background: accent.withValues(alpha: 0.1),
              ),
              _RunbookBadge(
                label: activeChain.incidentTargetLabel,
                foreground: tone,
                background: tone.withValues(alpha: 0.08),
              ),
              if (activeChain.isOverdue)
                const _RunbookBadge(
                  label: 'SLA 超时',
                  foreground: AppColors.error,
                  background: AppColors.errorLight,
                )
              else if (activeChain.escalationTier > 0)
                const _RunbookBadge(
                  label: '临近升级',
                  foreground: AppColors.warning,
                  background: AppColors.warningLight,
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(activeChain.runbookTitle, style: AppTextStyles.h4),
          const SizedBox(height: 6),
          Text(
            description,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            '${activeChain.ownerLabel} · SLA ${activeChain.slaMinutes}min · ${activeChain.escalationStateLabel}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (activeChain.slaDeadlineAt != null) ...[
            const SizedBox(height: 2),
            Text(
              'deadline ${DateFormat('MM-dd HH:mm').format(activeChain.slaDeadlineAt!.toLocal())} · ${activeChain.escalationLabel}',
              style: AppTextStyles.bodySmall.copyWith(
                color: activeChain.isOverdue
                    ? AppColors.error
                    : AppColors.textSecondary,
              ),
            ),
          ],
          const SizedBox(height: 14),
          for (var i = 0; i < activeChain.runbookSteps.length; i++) ...[
            _RunbookStep(
              index: i + 1,
              text: activeChain.runbookSteps[i],
              tone: tone,
            ),
            if (i < activeChain.runbookSteps.length - 1)
              const SizedBox(height: 10),
          ],
          const SizedBox(height: 14),
          _RunbookSignal(chain: activeChain, tone: tone, accent: accent),
          if (actions.isNotEmpty) ...[
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: actions
                  .map(
                    (action) => SizedBox(
                      width: 220,
                      child: _RunbookActionButton(action: action),
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }
}

class _RunbookSignal extends StatelessWidget {
  const _RunbookSignal({
    required this.chain,
    required this.tone,
    required this.accent,
  });

  final AssetChainSummary chain;
  final Color tone;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          tone.withValues(alpha: 0.05),
          AppColors.surfaceVariant,
        ),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: tone.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Text('Current watch', style: AppTextStyles.labelMedium),
              _RunbookBadge(
                label: chain.incidentTargetLabel,
                foreground: tone,
                background: tone.withValues(alpha: 0.1),
              ),
              _RunbookBadge(
                label: chain.sectionTargetLabel,
                foreground: accent,
                background: accent.withValues(alpha: 0.08),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            chain.incidentBrief,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${chain.workspaceTargetLabel} · ${chain.workspaceBrief}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _RunbookActionButton extends StatelessWidget {
  const _RunbookActionButton({required this.action});

  final WorkbenchCommandAction action;

  @override
  Widget build(BuildContext context) {
    final icon = action.isLoading
        ? const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : Icon(action.icon);

    final label = Text(action.label);

    switch (action.tone) {
      case WorkbenchCommandTone.primary:
        return FilledButton.icon(
          onPressed: action.isLoading ? null : action.onTap,
          icon: icon,
          label: label,
          style: FilledButton.styleFrom(
            backgroundColor: AppColors.cta,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
          ),
        );
      case WorkbenchCommandTone.tonal:
        return FilledButton.tonalIcon(
          onPressed: action.isLoading ? null : action.onTap,
          icon: icon,
          label: label,
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
          ),
        );
      case WorkbenchCommandTone.outline:
        return OutlinedButton.icon(
          onPressed: action.isLoading ? null : action.onTap,
          icon: icon,
          label: label,
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
          ),
        );
    }
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
