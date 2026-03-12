/// Operations Hub asset inventory board
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';
import 'incident_card_header.dart';
import 'workspace_action_lane.dart';

class AssetInventoryBoard extends StatelessWidget {
  const AssetInventoryBoard({
    super.key,
    required this.summary,
    required this.onNavigateToTab,
    this.onOpenChain,
    this.alerts = const <DashboardAlert>[],
  });

  final AssetSummary summary;
  final ValueChanged<int> onNavigateToTab;
  final ValueChanged<AssetChainSummary>? onOpenChain;
  final List<DashboardAlert> alerts;

  @override
  Widget build(BuildContext context) {
    final chainByKey = <String, AssetChainSummary>{
      for (final chain in summary.chainSummaries) chain.key: chain,
    };
    final latestDataset = summary.datasets.isEmpty
        ? null
        : summary.datasets.first;
    final latestModel = summary.models.isEmpty ? null : summary.models.first;
    final latestKnowledge = summary.knowledgeBases.isEmpty
        ? null
        : summary.knowledgeBases.first;
    final latestOptimization = summary.optimizations.isEmpty
        ? null
        : summary.optimizations.first;

    final datasetChain = chainByKey['dataset'];
    final modelChain = chainByKey['model'];
    final knowledgeChain = chainByKey['knowledge'];
    final optimizationChain = chainByKey['optimization'];

    final cards = [
      _AssetInventoryCard(
        title: '数据资产',
        accent: AppColors.primary,
        icon: Icons.dataset_rounded,
        count: summary.inventory.datasetAssets,
        chain: datasetChain,
        alert: _alertFor('dataset'),
        version: latestDataset == null
            ? '--'
            : _formatVersion(latestDataset.createdAt),
        headline: latestDataset?.filename ?? '暂无资产',
        details: [
          'quality=${latestDataset?.qualityScore?.toStringAsFixed(1) ?? '--'}',
          'rows=${latestDataset?.rows ?? '--'}',
          'cols=${latestDataset?.columns ?? '--'}',
        ],
        actionLabel: datasetChain?.actionLabel ?? '打开数据分析',
        onTap: () => _openAssetChain(datasetChain, fallbackTab: 2),
      ),
      _AssetInventoryCard(
        title: '模型产物',
        accent: AppColors.cta,
        icon: Icons.model_training_rounded,
        count: summary.inventory.modelAssets,
        chain: modelChain,
        alert: _alertFor('model'),
        version: latestModel?.version ?? '--',
        headline: latestModel == null
            ? '暂无模型'
            : '${(latestModel.modelType ?? 'model').toUpperCase()} / ${latestModel.targetColumn ?? '--'}',
        details: [
          'path=${latestModel?.modelPath ?? '--'}',
          'source=${latestModel?.storagePath ?? '--'}',
          'attempt=${latestModel?.attemptCount ?? '--'}/${latestModel?.maxAttempts ?? '--'}',
        ],
        actionLabel: modelChain?.actionLabel ?? '打开 AI Lab',
        onTap: () => _openAssetChain(modelChain, fallbackTab: 3),
      ),
      _AssetInventoryCard(
        title: '知识快照',
        accent: AppColors.success,
        icon: Icons.account_tree_rounded,
        count: summary.inventory.knowledgeAssets,
        chain: knowledgeChain,
        alert: _alertFor('knowledge'),
        version: latestKnowledge?.version ?? '--',
        headline: latestKnowledge?.collection ?? '暂无知识快照',
        details: [
          'docs=${latestKnowledge?.count ?? '--'}',
          'source=${latestKnowledge?.storagePath ?? '--'}',
          'mode=${latestKnowledge?.reset == true ? 'reset' : 'incremental'}',
        ],
        actionLabel: knowledgeChain?.actionLabel ?? '打开 AI Lab',
        onTap: () => _openAssetChain(knowledgeChain, fallbackTab: 3),
      ),
      _AssetInventoryCard(
        title: '优化快照',
        accent: AppColors.warning,
        icon: Icons.bolt_rounded,
        count: summary.inventory.optimizationAssets,
        chain: optimizationChain,
        alert: _alertFor('optimization'),
        version: latestOptimization?.version ?? '--',
        headline: latestOptimization == null
            ? '暂无优化结果'
            : 'target=${latestOptimization.targetDate ?? '--'}',
        details: [
          'soc=${_formatPercent(latestOptimization?.initialSoc)}',
          'capacity=${_formatNumber(latestOptimization?.batteryCapacity, suffix: 'kWh')}',
          'savings=${_formatNumber(latestOptimization?.savings, suffix: '元')}',
        ],
        actionLabel: optimizationChain?.actionLabel ?? '打开能源优化',
        onTap: () => _openAssetChain(optimizationChain, fallbackTab: 1),
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1080;
        if (compact) {
          return Column(
            children: [
              for (var i = 0; i < cards.length; i++) ...[
                cards[i],
                if (i < cards.length - 1) const SizedBox(height: 12),
              ],
            ],
          );
        }

        return Wrap(
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
      },
    );
  }

  DashboardAlert? _alertFor(String assetKey) {
    return alerts.cast<DashboardAlert?>().firstWhere(
      (alert) => alert?.assetKey == assetKey,
      orElse: () => null,
    );
  }

  void _openAssetChain(AssetChainSummary? chain, {required int fallbackTab}) {
    if (chain != null && onOpenChain != null) {
      onOpenChain!(chain);
      return;
    }
    onNavigateToTab(fallbackTab);
  }
}

class _AssetInventoryCard extends StatelessWidget {
  const _AssetInventoryCard({
    required this.title,
    required this.accent,
    required this.icon,
    required this.count,
    required this.chain,
    required this.alert,
    required this.version,
    required this.headline,
    required this.details,
    required this.actionLabel,
    required this.onTap,
  });

  final String title;
  final Color accent;
  final IconData icon;
  final int count;
  final AssetChainSummary? chain;
  final DashboardAlert? alert;
  final String version;
  final String headline;
  final List<String> details;
  final String actionLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final borderColor = chain != null
        ? _chainBorderColor(chain!)
        : accent.withValues(alpha: 0.14);
    final inventorySummary =
        'inventory=$count · latest v$version${chain == null ? '' : ' · ${chain!.statusLabel}'}';

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: borderColor),
      ),
      child: GlassCard(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            IncidentCardHeader(
              accent: accent,
              icon: icon,
              title: title,
              subtitle: '资产库存、最新版本和当前处置入口。',
              supportingText: inventorySummary,
              supportingColor: AppColors.textSecondary,
              trailing: alert == null ? null : _AlertBadge(alert: alert!),
              workspaceLabel: chain?.workspaceTargetLabel,
              cardLabel: chain?.cardTargetLabel,
              incidentLabel: chain?.incidentTargetLabel,
              summary: chain?.workspaceBrief,
            ),
            const SizedBox(height: 14),
            WorkspaceInlineActionBar(
              actions: [
                WorkspaceActionLaneAction(
                  label: actionLabel,
                  icon: Icons.arrow_outward_rounded,
                  onTap: onTap,
                  tone: WorkspaceActionLaneTone.tonal,
                ),
              ],
            ),
            const SizedBox(height: 14),
            Text(headline, style: AppTextStyles.labelLarge),
            if (alert != null) ...[
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: _severityColor(
                    alert!.severity,
                  ).withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                  border: Border.all(
                    color: _severityColor(
                      alert!.severity,
                    ).withValues(alpha: 0.16),
                  ),
                ),
                child: Text(
                  alert!.message,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 10),
            for (var i = 0; i < details.length; i++) ...[
              Text(
                details[i],
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              if (i < details.length - 1) const SizedBox(height: 4),
            ],
          ],
        ),
      ),
    );
  }
}

class _AlertBadge extends StatelessWidget {
  const _AlertBadge({required this.alert});

  final DashboardAlert alert;

  @override
  Widget build(BuildContext context) {
    final color = _severityColor(alert.severity);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        alert.severity.toUpperCase(),
        style: AppTextStyles.labelMedium.copyWith(color: color),
      ),
    );
  }
}

String _formatVersion(DateTime? value) {
  if (value == null) {
    return '--';
  }
  return DateFormat('MMdd-HHmm').format(value.toLocal());
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

Color _severityColor(String severity) {
  switch (severity) {
    case 'error':
      return AppColors.error;
    case 'warning':
      return AppColors.warning;
    case 'info':
      return AppColors.primary;
    default:
      return AppColors.textSecondary;
  }
}

Color _chainBorderColor(AssetChainSummary chain) {
  if (chain.isOverdue || chain.status == 'incident') {
    return AppColors.error.withValues(alpha: 0.28);
  }
  if (chain.status == 'active' || chain.status == 'attention') {
    return AppColors.warning.withValues(alpha: 0.26);
  }
  return _chainAccent(chain.key).withValues(alpha: 0.18);
}

Color _chainAccent(String key) {
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
