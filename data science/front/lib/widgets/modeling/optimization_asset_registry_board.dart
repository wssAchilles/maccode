/// Optimization asset registry board
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../models/job_record.dart';
import '../common/glass_card.dart';

class OptimizationAssetRegistryBoard extends StatelessWidget {
  const OptimizationAssetRegistryBoard({
    super.key,
    this.chain,
    required this.assetSummary,
    required this.latestCompletedJob,
    required this.onApplyAsset,
    required this.onCopyAssetPassport,
    required this.onLoadLatestJobResult,
  });

  final AssetChainSummary? chain;
  final AssetSummary? assetSummary;
  final JobRecord? latestCompletedJob;
  final ValueChanged<OptimizationAsset> onApplyAsset;
  final ValueChanged<OptimizationAsset> onCopyAssetPassport;
  final VoidCallback? onLoadLatestJobResult;

  @override
  Widget build(BuildContext context) {
    final latestAsset = assetSummary?.optimizations.isNotEmpty == true
        ? assetSummary!.optimizations.first
        : null;
    final inventoryCount = assetSummary?.inventory.optimizationAssets ?? 0;
    final assetSectionFocused = chain?.sectionTarget == 'optimization_assets';
    final cards = <Widget>[
      _RegistrySummaryCard(
        chain: chain,
        count: inventoryCount,
        latestVersion: latestAsset?.version ?? '--',
        latestTargetDate: latestAsset?.targetDate ?? '--',
      ),
      if (latestAsset != null)
        _OptimizationRegistryCard(
          chain: chain,
          asset: latestAsset,
          onApply: () => onApplyAsset(latestAsset),
          onCopyPassport: () => onCopyAssetPassport(latestAsset),
          onLoadLatestJobResult: onLoadLatestJobResult,
          latestCompletedJob: latestCompletedJob,
        )
      else
        const _RegistryEmptyCard(),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final stacked = constraints.maxWidth < 1100;
        final content = stacked
            ? Column(
                children: [
                  for (var i = 0; i < cards.length; i++) ...[
                    cards[i],
                    if (i < cards.length - 1) const SizedBox(height: 12),
                  ],
                ],
              )
            : Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 4, child: cards[0]),
                  const SizedBox(width: 12),
                  Expanded(flex: 6, child: cards[1]),
                ],
              );
        return _highlightShell(
          highlighted: assetSectionFocused,
          color: AppColors.warning,
          child: content,
        );
      },
    );
  }
}

class _RegistrySummaryCard extends StatelessWidget {
  const _RegistrySummaryCard({
    this.chain,
    required this.count,
    required this.latestVersion,
    required this.latestTargetDate,
  });

  final AssetChainSummary? chain;
  final int count;
  final String latestVersion;
  final String latestTargetDate;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(
                  Icons.inventory_2_rounded,
                  color: AppColors.warning,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('优化资产注册表', style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '统一资产摘要里的优化快照库存和最新版本。',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    if (chain?.sectionTarget == 'optimization_assets') ...[
                      const SizedBox(height: 6),
                      _RegistrySignal(
                        accent: AppColors.warning,
                        incidentLabel: chain?.incidentTargetLabel,
                        incidentSummary: chain?.incidentBrief,
                        sectionLabel: chain?.sectionTargetLabel,
                        focusLabel: chain?.focusLabel,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _RegistryChip(
                label: '库存',
                value: '$count',
                accent: AppColors.warning,
                icon: Icons.layers_rounded,
              ),
              _RegistryChip(
                label: '最新版本',
                value: latestVersion == '--' ? '--' : 'v$latestVersion',
                accent: AppColors.primary,
                icon: Icons.new_releases_rounded,
              ),
              _RegistryChip(
                label: '目标日期',
                value: latestTargetDate,
                accent: AppColors.success,
                icon: Icons.event_rounded,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _OptimizationRegistryCard extends StatelessWidget {
  const _OptimizationRegistryCard({
    this.chain,
    required this.asset,
    required this.onApply,
    required this.onCopyPassport,
    required this.onLoadLatestJobResult,
    required this.latestCompletedJob,
  });

  final AssetChainSummary? chain;
  final OptimizationAsset asset;
  final VoidCallback onApply;
  final VoidCallback onCopyPassport;
  final VoidCallback? onLoadLatestJobResult;
  final JobRecord? latestCompletedJob;

  @override
  Widget build(BuildContext context) {
    final completedAt = asset.completedAt == null
        ? '--'
        : DateFormat('MM-dd HH:mm').format(asset.completedAt!.toLocal());
    final latestJobMatches = latestCompletedJob?.jobId == asset.jobId;
    final card = GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('最新优化快照', style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '把登记到资产台账的优化快照回填到当前工作台，用于版本复盘和参数重放。',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    if (chain?.focusTarget == 'optimization_registry') ...[
                      const SizedBox(height: 6),
                      _RegistrySignal(
                        accent: AppColors.warning,
                        incidentLabel: chain?.incidentTargetLabel,
                        incidentSummary: chain?.incidentBrief,
                        sectionLabel: chain?.sectionTargetLabel,
                        focusLabel: chain?.focusLabel,
                      ),
                    ],
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(
                    AppDecorations.radiusFull,
                  ),
                ),
                child: Text(
                  'v${asset.version}',
                  style: AppTextStyles.labelMedium.copyWith(
                    color: AppColors.warning,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _Line(label: '目标日期', value: asset.targetDate ?? '--'),
          const SizedBox(height: 8),
          _Line(label: '初始 SOC', value: _formatPercent(asset.initialSoc)),
          const SizedBox(height: 8),
          _Line(
            label: '电池配置',
            value:
                '${_formatNumber(asset.batteryCapacity, suffix: 'kWh')} / ${_formatNumber(asset.batteryPower, suffix: 'kW')}',
          ),
          const SizedBox(height: 8),
          _Line(
            label: '节省表现',
            value:
                '${_formatNumber(asset.savings, suffix: '元')} · ${_formatPercent(asset.savingsPercent)}',
          ),
          const SizedBox(height: 8),
          _Line(
            label: '资产血缘',
            value:
                'job=${asset.jobId.isEmpty ? '--' : asset.jobId.substring(0, asset.jobId.length < 8 ? asset.jobId.length : 8)} · $completedAt',
          ),
          if (latestCompletedJob != null) ...[
            const SizedBox(height: 8),
            _Line(
              label: '后台回放',
              value: latestJobMatches
                  ? '当前快照已关联可回放后台结果'
                  : '存在较新的后台产物，可单独载入完整结果',
            ),
          ],
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.icon(
                onPressed: onApply,
                icon: const Icon(Icons.restart_alt_rounded),
                label: const Text('回填优化配置'),
              ),
              OutlinedButton.icon(
                onPressed: onCopyPassport,
                icon: const Icon(Icons.badge_rounded),
                label: const Text('复制优化护照'),
              ),
              if (onLoadLatestJobResult != null)
                OutlinedButton.icon(
                  onPressed: onLoadLatestJobResult,
                  icon: const Icon(Icons.download_done_rounded),
                  label: Text(latestJobMatches ? '载入完整结果' : '载入最近后台结果'),
                ),
            ],
          ),
        ],
      ),
    );
    return _highlightShell(
      highlighted: chain?.focusTarget == 'optimization_registry',
      color: AppColors.warning,
      child: card,
    );
  }
}

class _RegistryEmptyCard extends StatelessWidget {
  const _RegistryEmptyCard();

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('最新优化快照', style: AppTextStyles.h4),
          const SizedBox(height: 8),
          Text(
            '当前还没有统一登记到资产台账的优化快照。提交一次后台优化任务后，这里会出现可回填版本。',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _RegistryChip extends StatelessWidget {
  const _RegistryChip({
    required this.label,
    required this.value,
    required this.accent,
    required this.icon,
  });

  final String label;
  final String value;
  final Color accent;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: accent),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: AppTextStyles.labelMedium),
              const SizedBox(height: 2),
              Text(
                value,
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RegistrySignal extends StatelessWidget {
  const _RegistrySignal({
    required this.accent,
    this.incidentLabel,
    this.incidentSummary,
    this.sectionLabel,
    this.focusLabel,
  });

  final Color accent;
  final String? incidentLabel;
  final String? incidentSummary;
  final String? sectionLabel;
  final String? focusLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (incidentLabel != null)
                _RegistryChip(
                  label: 'Current watch',
                  value: incidentLabel!,
                  accent: accent,
                  icon: Icons.flag_rounded,
                ),
              if (focusLabel != null)
                _RegistryChip(
                  label: 'Target',
                  value: sectionLabel == null
                      ? focusLabel!
                      : '${sectionLabel!} · ${focusLabel!}',
                  accent: AppColors.primary,
                  icon: Icons.track_changes_rounded,
                ),
            ],
          ),
          if (incidentSummary != null) ...[
            const SizedBox(height: 8),
            Text(
              incidentSummary!,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ],
      ),
    );
  }
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
      border: Border.all(color: color.withValues(alpha: 0.32), width: 1.3),
    ),
    child: child,
  );
}

class _Line extends StatelessWidget {
  const _Line({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTextStyles.labelMedium),
        const SizedBox(height: 4),
        SelectableText(value, style: AppTextStyles.bodyMedium),
      ],
    );
  }
}

String _formatNumber(double? value, {required String suffix}) {
  if (value == null) {
    return '--';
  }
  return '${value.toStringAsFixed(1)}$suffix';
}

String _formatPercent(double? value) {
  if (value == null) {
    return '--';
  }
  return '${(value * 100).toStringAsFixed(0)}%';
}
