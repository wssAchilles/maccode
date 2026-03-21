library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../models/workbench_launch_context.dart';
import '../../utils/asset_chain_context.dart';
import '../common/glass_card.dart';

class WorkbenchSectionSignal extends StatelessWidget {
  const WorkbenchSectionSignal({
    super.key,
    required this.chain,
    required this.title,
    required this.description,
    required this.icon,
    this.continuationContext,
  });

  final AssetChainSummary? chain;
  final String title;
  final String description;
  final IconData icon;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final activeChain = chain;
    if (activeChain == null) {
      return const SizedBox.shrink();
    }

    final tone = _toneFor(activeChain);
    final workspaceLabel =
        continuationContext?.workspaceTargetLabel ??
        activeChain.workspaceTargetLabel;
    final cardLabel = buildDutyContextCardValue(
      continuationContext?.cardTargetLabel ?? activeChain.cardTargetLabel,
    );
    final incidentLabel = buildDutyContextIncidentValue(
      continuationContext?.incidentTargetLabel ??
          activeChain.incidentTargetLabel,
    );
    final watchSummary = _watchValue(
      activeChain,
      continuationContext,
      workspaceLabel: workspaceLabel,
      cardLabel: cardLabel,
      incidentLabel: incidentLabel,
    );
    final sectionTarget = [workspaceLabel, cardLabel]
        .whereType<String>()
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .join(' · ');

    final facts = [
      _SignalFact(
        label: '当前关注',
        value: watchSummary,
        highlighted:
            _signalHighlight(activeChain, continuationContext) ==
            _SignalFocus.watch,
        accent: tone,
      ),
      _SignalFact(
        label: '落点区域',
        value: sectionTarget.isEmpty ? workspaceLabel : sectionTarget,
        accent: tone,
      ),
      _SignalFact(
        label: '执行态',
        value: _executionValue(activeChain, continuationContext),
        highlighted:
            _signalHighlight(activeChain, continuationContext) ==
            _SignalFocus.execution,
        accent: tone,
      ),
      _SignalFact(
        label: '值班状态',
        value: _dutyValue(activeChain),
        highlighted:
            _signalHighlight(activeChain, continuationContext) ==
            _SignalFocus.duty,
        accent: tone,
      ),
    ];

    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 980;

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
                              label: workspaceLabel,
                              foreground: tone,
                              background: tone.withValues(alpha: 0.08),
                            ),
                            if (cardLabel != null)
                              _SignalBadge(
                                label: cardLabel,
                                foreground: AppColors.textPrimary,
                                background: AppColors.surfaceVariant,
                              ),
                            if (incidentLabel != null)
                              _SignalBadge(
                                label: incidentLabel,
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

String _executionValue(
  AssetChainSummary chain,
  WorkbenchLaunchContext? continuationContext,
) {
  final normalizedStatus = _normalizeExecutionToken(chain.jobStatus);
  final normalizedPhase = _normalizeExecutionToken(chain.jobPhase);
  final progress = chain.jobProgress;
  final progressComplete = progress >= 100;

  if (normalizedStatus != null) {
    if ((normalizedStatus == '已完成' || normalizedStatus == '完成') &&
        (progressComplete || normalizedPhase == null)) {
      return '已完成';
    }
    if (normalizedStatus == '运行中' && normalizedPhase != null) {
      return '$normalizedStatus · $normalizedPhase';
    }
    if (normalizedStatus == '失败' && normalizedPhase != null) {
      return '$normalizedStatus · $normalizedPhase';
    }
    return normalizedStatus;
  }

  if (chain.failurePhase != '--') {
    final failurePhase = _normalizeExecutionToken(chain.failurePhase);
    final failureSource = _normalizeExecutionToken(chain.failureSource);
    return [
      failurePhase ?? '失败',
      failureSource,
    ].whereType<String>().where((value) => value.isNotEmpty).join(' · ');
  }

  final workspaceLabel =
      continuationContext?.workspaceTargetLabel ?? chain.workspaceTargetLabel;
  final cardLabel = buildDutyContextCardValue(
    continuationContext?.cardTargetLabel ?? chain.cardTargetLabel,
  );
  final incidentLabel = buildDutyContextIncidentValue(
    continuationContext?.incidentTargetLabel ?? chain.incidentTargetLabel,
  );
  final latestVersion = chain.latestVersion.trim();
  final normalizedLatestVersion =
      latestVersion.isNotEmpty &&
          latestVersion != '--' &&
          !latestVersion.startsWith('v')
      ? 'v$latestVersion'
      : latestVersion;
  final latestLabel = sanitizeWorkspaceSummaryText(
    chain.latestLabel,
    duplicatedLabels: [workspaceLabel, cardLabel, incidentLabel],
  );
  final parts = <String>[
    if (normalizedLatestVersion.isNotEmpty && normalizedLatestVersion != '--')
      '最新版本 $normalizedLatestVersion',
    if (latestLabel != null && latestLabel.isNotEmpty) latestLabel,
  ];
  if (parts.isNotEmpty) {
    return parts.join(' · ');
  }
  return workspaceLabel;
}

String _dutyValue(AssetChainSummary chain) {
  final parts = [
    chain.ownerLabel.trim(),
    chain.escalationStateLabel.trim(),
  ].where((value) => value.isNotEmpty && value != '--').toList(growable: false);
  if (parts.isEmpty) {
    return '--';
  }
  return parts.join(' · ');
}

String? _normalizeExecutionToken(String? value) {
  final normalized = value?.trim();
  if (normalized == null || normalized.isEmpty || normalized == '--') {
    return null;
  }
  switch (normalized.toLowerCase()) {
    case 'succeeded':
    case 'completed':
      return '已完成';
    case 'running':
    case 'started':
      return '运行中';
    case 'queued':
      return '已排队';
    case 'failed':
      return '失败';
    case 'healthy':
      return '健康';
    case 'idle':
      return '空闲';
  }
  switch (normalized) {
    case '处理中':
      return null;
    case '已完成':
    case '运行中':
    case '已排队':
    case '失败':
      return normalized;
  }
  return normalized;
}

String _watchValue(
  AssetChainSummary chain,
  WorkbenchLaunchContext? continuationContext, {
  required String workspaceLabel,
  required String? cardLabel,
  required String? incidentLabel,
}) {
  final rawWatchSummary = continuationContext?.watchSummary ?? chain.incidentBrief;
  final cleanedWatchSummary = sanitizeWorkspaceSummaryText(
    rawWatchSummary,
    duplicatedLabels: [workspaceLabel, cardLabel, incidentLabel],
  );

  final watchSummary =
      chain.isOverdue || chain.status == 'incident'
          ? cleanedWatchSummary
          : buildWorkspaceSummaryText(
              workspaceTarget:
                  continuationContext?.workspaceTarget ?? chain.workspaceTarget,
              workspaceTargetLabel: workspaceLabel,
              workspaceBrief: chain.workspaceBrief,
              incidentBrief: cleanedWatchSummary ?? rawWatchSummary,
              cardTargetLabel: cardLabel,
              incidentTargetLabel: incidentLabel,
              sectionTargetLabel: chain.sectionTargetLabel,
              focusTargetLabel: chain.focusTargetLabel,
            );

  return buildIncidentWatchValue(
    incidentLabel,
    watchSummary == '--' ? null : watchSummary,
  );
}

enum _SignalFocus { watch, execution, duty }

_SignalFocus _signalHighlight(
  AssetChainSummary chain,
  WorkbenchLaunchContext? continuationContext,
) {
  switch (continuationContext?.incidentTarget ?? chain.incidentTarget) {
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
