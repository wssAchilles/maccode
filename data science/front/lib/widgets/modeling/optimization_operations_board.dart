/// Optimization operational telemetry board
library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../models/job_record.dart';
import '../../models/optimization_result.dart';
import '../common/glass_card.dart';
import '../operations/asset_chain_section_header.dart';

class OptimizationOperationsBoard extends StatelessWidget {
  const OptimizationOperationsBoard({
    super.key,
    required this.chain,
    required this.result,
    required this.latestCompletedJob,
  });

  final AssetChainSummary? chain;
  final OptimizationResponse? result;
  final JobRecord? latestCompletedJob;

  @override
  Widget build(BuildContext context) {
    final optimization = result?.optimization;
    final diagnostics = optimization?.diagnostics;
    final hits = optimization?.constraintHits;
    final explainability = result?.modelExplainability;
    final solverHealth = _solverHealth(diagnostics);
    final totalConstraintHits = hits == null
        ? 0
        : hits.socMinHits +
              hits.socMaxHits +
              hits.maxChargeHits +
              hits.maxDischargeHits;

    final cards = [
      _TelemetryCard(
        title: '求解器健康',
        accent: solverHealth.color,
        icon: Icons.monitor_heart_rounded,
        badge: solverHealth.label,
        highlighted: _focusTelemetryCard(chain, 'solver'),
        noteLabel: _focusTelemetryCard(chain, 'solver')
            ? chain?.incidentTargetLabel
            : null,
        note: _focusTelemetryCard(chain, 'solver')
            ? chain?.incidentBrief
            : null,
        lines: [
          'runtime=${diagnostics?.runtimeLabel ?? '--'}',
          'mip_gap=${diagnostics?.mipGap?.toStringAsFixed(4) ?? '--'}',
          'nodes=${diagnostics?.nodeCount ?? '--'} · iter=${diagnostics?.iterCount ?? '--'}',
        ],
      ),
      _TelemetryCard(
        title: '约束压力',
        accent: totalConstraintHits > 12
            ? AppColors.warning
            : AppColors.success,
        icon: Icons.rule_folder_rounded,
        badge: totalConstraintHits == 0
            ? 'LOW'
            : totalConstraintHits > 12
            ? 'HIGH'
            : 'MEDIUM',
        highlighted: _focusTelemetryCard(chain, 'constraint'),
        noteLabel: _focusTelemetryCard(chain, 'constraint')
            ? chain?.incidentTargetLabel
            : null,
        note: _focusTelemetryCard(chain, 'constraint')
            ? chain?.incidentBrief
            : null,
        lines: [
          'soc_min=${hits?.socMinHits ?? 0}',
          'soc_max=${hits?.socMaxHits ?? 0}',
          'charge_cap=${hits?.maxChargeHits ?? 0} · discharge_cap=${hits?.maxDischargeHits ?? 0}',
        ],
      ),
      _TelemetryCard(
        title: '解释性前哨',
        accent: AppColors.primary,
        icon: Icons.insights_rounded,
        badge: explainability?.topFeature == null
            ? 'N/A'
            : explainability!.topFeaturePercent,
        highlighted: _focusTelemetryCard(chain, 'explainability'),
        noteLabel: _focusTelemetryCard(chain, 'explainability')
            ? chain?.incidentTargetLabel
            : null,
        note: _focusTelemetryCard(chain, 'explainability')
            ? chain?.incidentBrief
            : null,
        lines: [
          'top_feature=${explainability?.topFeature ?? '--'}',
          if ((explainability?.interpretation ?? '').isNotEmpty)
            explainability!.interpretation!,
          if ((explainability?.interpretation ?? '').isEmpty)
            '结果可用于判断当前调度更受哪类变量影响。',
        ],
      ),
      _TelemetryCard(
        title: '最近产物',
        accent: AppColors.cta,
        icon: Icons.inventory_2_rounded,
        badge: latestCompletedJob == null
            ? 'IDLE'
            : latestCompletedJob!.jobId.substring(0, 8),
        highlighted: _focusTelemetryCard(chain, 'artifact'),
        noteLabel: _focusTelemetryCard(chain, 'artifact')
            ? chain?.incidentTargetLabel
            : null,
        note: _focusTelemetryCard(chain, 'artifact')
            ? chain?.incidentBrief
            : null,
        lines: [
          'status=${latestCompletedJob?.statusMessage ?? latestCompletedJob?.status ?? '--'}',
          'attempt=${latestCompletedJob?.attemptCount ?? '--'}/${latestCompletedJob?.maxAttempts ?? '--'}',
          'ready=${latestCompletedJob != null ? 'yes' : 'no'}',
        ],
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1080;
        final grid = compact
            ? Column(
                children: [
                  for (var i = 0; i < cards.length; i++) ...[
                    cards[i],
                    if (i < cards.length - 1) const SizedBox(height: 12),
                  ],
                ],
              )
            : Wrap(
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

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AssetChainSectionHeader(
              title: '优化运维视图',
              subtitle: '把求解器健康、约束压力、解释性前哨和最近产物放到同一块运行摘要里。',
              chain: chain,
              icon: Icons.monitor_heart_rounded,
            ),
            const SizedBox(height: 16),
            grid,
          ],
        );
      },
    );
  }
}

class _TelemetryCard extends StatelessWidget {
  const _TelemetryCard({
    required this.title,
    required this.accent,
    required this.icon,
    required this.badge,
    required this.highlighted,
    this.noteLabel,
    this.note,
    required this.lines,
  });

  final String title;
  final Color accent;
  final IconData icon;
  final String badge;
  final bool highlighted;
  final String? noteLabel;
  final String? note;
  final List<String> lines;

  @override
  Widget build(BuildContext context) {
    final card = GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: accent),
              const SizedBox(width: 10),
              Expanded(child: Text(title, style: AppTextStyles.h4)),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(
                    AppDecorations.radiusFull,
                  ),
                ),
                child: Text(
                  badge,
                  style: AppTextStyles.labelMedium.copyWith(color: accent),
                ),
              ),
            ],
          ),
          if (highlighted && note != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (noteLabel != null)
                    Text(
                      'Current watch · $noteLabel',
                      style: AppTextStyles.labelMedium.copyWith(color: accent),
                    ),
                  if (noteLabel != null) const SizedBox(height: 4),
                  Text(
                    note!,
                    style: AppTextStyles.bodySmall.copyWith(color: accent),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          for (var i = 0; i < lines.length; i++) ...[
            Text(
              lines[i],
              style: AppTextStyles.bodySmall.copyWith(
                color: i == 0 ? AppColors.textPrimary : AppColors.textSecondary,
              ),
            ),
            if (i < lines.length - 1) const SizedBox(height: 6),
          ],
        ],
      ),
    );
    return _highlightShell(
      highlighted: highlighted,
      color: accent,
      child: card,
    );
  }
}

bool _focusTelemetryCard(AssetChainSummary? chain, String section) {
  if (chain == null) {
    return false;
  }
  if (chain.sectionTarget == 'optimization_assets') {
    return false;
  }
  switch (chain.focusTarget) {
    case 'optimization_solver':
      return section == 'solver';
    case 'optimization_constraint':
      return section == 'constraint';
    case 'optimization_explainability':
      return section == 'explainability';
    case 'optimization_registry':
    case 'optimization_job_panel':
      return section == 'artifact';
  }
  if (chain.status == 'incident' || chain.status == 'active') {
    return section == 'artifact';
  }
  if (chain.status == 'watch') {
    return section == 'constraint';
  }
  return section == 'artifact';
}

Widget _highlightShell({
  required bool highlighted,
  required Color color,
  required Widget child,
}) {
  if (!highlighted) {
    return child;
  }
  return Container(
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
      border: Border.all(color: color.withValues(alpha: 0.32)),
    ),
    child: child,
  );
}

class _SolverHealthState {
  const _SolverHealthState({required this.label, required this.color});

  final String label;
  final Color color;
}

_SolverHealthState _solverHealth(SolverDiagnostics? diagnostics) {
  if (diagnostics == null) {
    return const _SolverHealthState(
      label: 'UNKNOWN',
      color: AppColors.textSecondary,
    );
  }
  final runtime = diagnostics.runtimeSec;
  final gap = diagnostics.mipGap ?? 0;
  if (runtime > 30 || gap > 0.03) {
    return const _SolverHealthState(label: 'WATCH', color: AppColors.warning);
  }
  return const _SolverHealthState(label: 'HEALTHY', color: AppColors.success);
}
