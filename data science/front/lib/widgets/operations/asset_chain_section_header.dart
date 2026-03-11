library;

import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';

class AssetChainSectionHeader extends StatelessWidget {
  const AssetChainSectionHeader({
    super.key,
    required this.title,
    required this.subtitle,
    this.chain,
    this.icon,
  });

  final String title;
  final String subtitle;
  final AssetChainSummary? chain;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final activeChain = chain;
    final tone = activeChain == null
        ? AppColors.primary
        : _toneFor(activeChain);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (icon != null) ...[
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: tone.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Icon(icon, color: tone, size: 20),
          ),
          const SizedBox(width: 12),
        ],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  Text(title, style: AppTextStyles.h4),
                  if (activeChain != null)
                    _HeaderBadge(
                      label: activeChain.statusLabel,
                      foreground: tone,
                      background: tone.withValues(alpha: 0.12),
                    ),
                  if (activeChain != null)
                    _HeaderBadge(
                      label: activeChain.workspaceTargetLabel,
                      foreground: tone,
                      background: tone.withValues(alpha: 0.08),
                    ),
                  if (activeChain?.isOverdue == true)
                    const _HeaderBadge(
                      label: 'SLA 超时',
                      foreground: AppColors.error,
                      background: AppColors.errorLight,
                    ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              if (activeChain != null) ...[
                const SizedBox(height: 6),
                Text(
                  '${activeChain.workspaceTargetLabel} · ${activeChain.workspaceBrief}',
                  style: AppTextStyles.bodySmall.copyWith(color: tone),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _HeaderBadge extends StatelessWidget {
  const _HeaderBadge({
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
