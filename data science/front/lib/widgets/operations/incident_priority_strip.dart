library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../utils/asset_chain_context.dart';

class IncidentPriorityStrip extends StatelessWidget {
  const IncidentPriorityStrip({
    super.key,
    required this.summary,
    required this.onOpenChain,
    this.dutySummary,
  });

  final AssetSummary summary;
  final ValueChanged<AssetChainSummary> onOpenChain;
  final DutySummary? dutySummary;

  @override
  Widget build(BuildContext context) {
    final chains = [...summary.chainSummaries]
      ..sort((a, b) => compareChainsByDutyFocus(a, b, dutySummary));
    final items = chains.take(4).toList(growable: false);
    if (items.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFF7FAFF), Color(0xFFFDF7ED)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 1180;
          final children = items
              .map(
                (chain) => _PriorityStripTile(
                  chain: chain,
                  isDutyFocus: isDutyFocusChain(chain, dutySummary),
                  onTap: () => onOpenChain(chain),
                ),
              )
              .toList(growable: false);

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StripHeader(count: items.length),
                const SizedBox(height: 12),
                for (var i = 0; i < children.length; i++) ...[
                  children[i],
                  if (i < children.length - 1) const SizedBox(height: 10),
                ],
              ],
            );
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StripHeader(count: items.length),
              const SizedBox(height: 12),
              Row(
                children: [
                  for (var i = 0; i < children.length; i++) ...[
                    Expanded(child: children[i]),
                    if (i < children.length - 1) const SizedBox(width: 10),
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

class _StripHeader extends StatelessWidget {
  const _StripHeader({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Incident Priority Strip', style: AppTextStyles.h4),
              const SizedBox(height: 4),
              Text(
                '把最需要值班关注的资产链路压成同一层，先看超时和升级，再进入具体工作台。',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            border: Border.all(color: AppColors.border),
          ),
          child: Text(
            '$count lanes',
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ),
      ],
    );
  }
}

class _PriorityStripTile extends StatelessWidget {
  const _PriorityStripTile({
    required this.chain,
    required this.onTap,
    required this.isDutyFocus,
  });

  final AssetChainSummary chain;
  final VoidCallback onTap;
  final bool isDutyFocus;

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(chain);
    final chainTone = _chainColor(chain.key);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: tone.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MiniBadge(
                label: chain.label,
                foreground: _chainColor(chain.key),
                background: _chainColor(chain.key).withValues(alpha: 0.12),
              ),
              _MiniBadge(
                label: chain.statusLabel,
                foreground: tone,
                background: tone.withValues(alpha: 0.12),
              ),
              _MiniBadge(
                label: chain.cardTargetLabel,
                foreground: chainTone,
                background: chainTone.withValues(alpha: 0.1),
              ),
              _MiniBadge(
                label: chain.workspaceTargetLabel,
                foreground: AppColors.textPrimary,
                background: AppColors.surfaceVariant,
              ),
              _MiniBadge(
                label: chain.incidentTargetLabel,
                foreground: tone,
                background: tone.withValues(alpha: 0.08),
              ),
              if (chain.isOverdue)
                _MiniBadge(
                  label: 'OVERDUE ${chain.overdueMinutes}m',
                  foreground: AppColors.error,
                  background: AppColors.errorLight,
                )
              else if (isDutyFocus)
                _MiniBadge(
                  label: 'DUTY FOCUS',
                  foreground: AppColors.primary,
                  background: AppColors.infoLight,
                )
              else if (chain.escalationTier > 0)
                _MiniBadge(
                  label: 'DUE SOON',
                  foreground: AppColors.warning,
                  background: AppColors.warningLight,
                ),
            ],
          ),
          const SizedBox(height: 10),
          Text(chain.cardTargetLabel, style: AppTextStyles.labelLarge),
          const SizedBox(height: 4),
          Text(
            chain.workspaceBrief,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          _PriorityFocusBand(chain: chain, accent: tone),
          const SizedBox(height: 10),
          Text(
            '${chain.ownerLabel} · ${chain.escalationStateLabel}',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          if (chain.slaDeadlineAt != null) ...[
            const SizedBox(height: 2),
            Text(
              'due ${DateFormat('MM-dd HH:mm').format(chain.slaDeadlineAt!.toLocal())} · ${chain.escalationLabel}',
              style: AppTextStyles.bodySmall.copyWith(
                color: chain.isOverdue
                    ? AppColors.error
                    : AppColors.textSecondary,
              ),
            ),
          ],
          const SizedBox(height: 12),
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

class _PriorityFocusBand extends StatelessWidget {
  const _PriorityFocusBand({required this.chain, required this.accent});

  final AssetChainSummary chain;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          accent.withValues(alpha: 0.05),
          AppColors.surfaceVariant,
        ),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Current watch',
                  style: AppTextStyles.labelMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
              _MiniBadge(
                label: chain.incidentTargetLabel,
                foreground: accent,
                background: accent.withValues(alpha: 0.1),
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
        ],
      ),
    );
  }
}

class _MiniBadge extends StatelessWidget {
  const _MiniBadge({
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
