library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';

class WorkbenchSectionSignal extends StatelessWidget {
  const WorkbenchSectionSignal({
    super.key,
    required this.chain,
    required this.title,
    required this.description,
    required this.icon,
  });

  final AssetChainSummary? chain;
  final String title;
  final String description;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final activeChain = chain;
    if (activeChain == null) {
      return const SizedBox.shrink();
    }

    final tone = _toneFor(activeChain);

    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 980;
          final facts = [
            _SignalFact(
              label: 'Current Watch',
              value:
                  '${activeChain.incidentTargetLabel} · ${activeChain.incidentBrief}',
              highlighted: _signalHighlight(activeChain) == _SignalFocus.watch,
              accent: tone,
            ),
            _SignalFact(
              label: 'Section Target',
              value:
                  '${activeChain.workspaceTargetLabel} · ${activeChain.sectionTargetLabel}',
              accent: tone,
            ),
            _SignalFact(
              label: '执行态',
              value: _executionValue(activeChain),
              highlighted:
                  _signalHighlight(activeChain) == _SignalFocus.execution,
              accent: tone,
            ),
            _SignalFact(
              label: '值班状态',
              value:
                  '${activeChain.ownerLabel} · ${activeChain.escalationStateLabel}',
              highlighted: _signalHighlight(activeChain) == _SignalFocus.duty,
              accent: tone,
            ),
          ];

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: tone.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(
                        AppDecorations.radiusMd,
                      ),
                    ),
                    child: Icon(icon, color: tone, size: 20),
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
                            Text(title, style: AppTextStyles.h4),
                            _SignalBadge(
                              label: activeChain.statusLabel,
                              foreground: tone,
                              background: tone.withValues(alpha: 0.12),
                            ),
                            _SignalBadge(
                              label: activeChain.workspaceTargetLabel,
                              foreground: tone,
                              background: tone.withValues(alpha: 0.08),
                            ),
                            _SignalBadge(
                              label: activeChain.incidentTargetLabel,
                              foreground: tone,
                              background: tone.withValues(alpha: 0.08),
                            ),
                            if (activeChain.isOverdue)
                              const _SignalBadge(
                                label: 'SLA 超时',
                                foreground: AppColors.error,
                                background: AppColors.errorLight,
                              ),
                          ],
                        ),
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
              const SizedBox(height: 14),
              if (compact)
                Column(
                  children: [
                    for (var i = 0; i < facts.length; i++) ...[
                      facts[i],
                      if (i < facts.length - 1) const SizedBox(height: 10),
                    ],
                  ],
                )
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (var i = 0; i < facts.length; i++) ...[
                      Expanded(child: facts[i]),
                      if (i < facts.length - 1) const SizedBox(width: 12),
                    ],
                  ],
                ),
            ],
          );
        },
      ),
    );
  }
}

class _SignalFact extends StatelessWidget {
  const _SignalFact({
    required this.label,
    required this.value,
    this.highlighted = false,
    this.accent = AppColors.primary,
  });

  final String label;
  final String value;
  final bool highlighted;
  final Color accent;

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
          color: highlighted
              ? accent.withValues(alpha: 0.18)
              : AppColors.border,
          width: highlighted ? 1.3 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTextStyles.labelMedium.copyWith(
              color: highlighted ? accent : AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 4),
          Text(value, style: AppTextStyles.bodySmall),
        ],
      ),
    );
  }
}

class _SignalBadge extends StatelessWidget {
  const _SignalBadge({
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

String _executionValue(AssetChainSummary chain) {
  if (chain.jobStatus != '--') {
    return '${chain.jobStatus} · ${chain.jobPhase} · ${chain.jobProgress}%';
  }
  if (chain.failurePhase != '--') {
    return '${chain.failurePhase} · ${chain.failureSource}';
  }
  return 'latest v${chain.latestVersion} · ${chain.latestLabel} · ${chain.workspaceTargetLabel}';
}

enum _SignalFocus { watch, execution, duty }

_SignalFocus _signalHighlight(AssetChainSummary chain) {
  switch (chain.incidentTarget) {
    case 'sla':
      return _SignalFocus.duty;
    case 'runtime':
      return _SignalFocus.execution;
    case 'activity':
    case 'asset':
    case 'failure':
    case 'focus':
    default:
      return _SignalFocus.watch;
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
