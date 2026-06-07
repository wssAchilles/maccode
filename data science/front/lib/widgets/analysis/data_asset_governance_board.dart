/// 数据资产治理与漂移检测面板
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/data_drift_report.dart';
import '../../models/dashboard_summary.dart';
import '../../models/history_record.dart';
import '../../models/workbench_launch_context.dart';
import '../common/glass_card.dart';
import '../operations/asset_chain_section_header.dart';
import '../operations/incident_card_header.dart';
import '../operations/workspace_action_lane.dart';

class DataAssetGovernanceBoard extends StatelessWidget {
  const DataAssetGovernanceBoard({
    super.key,
    this.chain,
    this.continuationContext,
    required this.currentStoragePath,
    required this.currentQualityScore,
    required this.currentAssetLabel,
    required this.referenceAssets,
    required this.selectedReferencePath,
    required this.availableFeatures,
    required this.selectedFeatures,
    required this.isLoadingAssets,
    required this.isRunningDrift,
    required this.onSelectReference,
    required this.onToggleFeature,
    required this.onRefreshAssets,
    required this.onRunDrift,
    required this.onCopyCurrentPath,
    required this.onCopyDriftReport,
    this.assetsErrorMessage,
    this.driftErrorMessage,
    this.report,
  });

  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;
  final String? currentStoragePath;
  final double? currentQualityScore;
  final String currentAssetLabel;
  final List<HistoryRecord> referenceAssets;
  final String? selectedReferencePath;
  final List<String> availableFeatures;
  final Set<String> selectedFeatures;
  final bool isLoadingAssets;
  final bool isRunningDrift;
  final VoidCallback onRefreshAssets;
  final VoidCallback onRunDrift;
  final VoidCallback onCopyCurrentPath;
  final VoidCallback onCopyDriftReport;
  final ValueChanged<String?> onSelectReference;
  final ValueChanged<String> onToggleFeature;
  final String? assetsErrorMessage;
  final String? driftErrorMessage;
  final DataDriftReport? report;

  @override
  Widget build(BuildContext context) {
    final selectedReference = referenceAssets.cast<HistoryRecord?>().firstWhere(
      (item) => item?.storageUrl == selectedReferencePath,
      orElse: () => null,
    );
    final canRunDrift =
        currentStoragePath != null &&
        currentStoragePath!.isNotEmpty &&
        selectedReferencePath != null &&
        selectedReferencePath!.isNotEmpty &&
        selectedFeatures.isNotEmpty &&
        !isRunningDrift;
    final focusArea = _focusArea(
      chain,
      continuationContext: continuationContext,
      hasCurrentAsset:
          currentStoragePath != null && currentStoragePath!.isNotEmpty,
      hasReference:
          selectedReferencePath != null && selectedReferencePath!.isNotEmpty,
      hasReport: report != null,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AssetChainSectionHeader(
          title: '资产治理与漂移检测',
          subtitle: '围绕当前数据链路完成资产基线选择、漂移检测和治理结论，不把治理动作埋在结果区之后。',
          chain: chain,
          continuationContext: continuationContext,
          icon: Icons.analytics_rounded,
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final stacked = constraints.maxWidth < 1080;
            final cards = [
              _CurrentAssetCard(
                highlighted: focusArea == 'current',
                chain: chain,
                continuationContext: continuationContext,
                currentAssetLabel: currentAssetLabel,
                currentStoragePath: currentStoragePath,
                currentQualityScore: currentQualityScore,
                onCopyCurrentPath: onCopyCurrentPath,
              ),
              _ReferenceAssetCard(
                highlighted: focusArea == 'reference',
                chain: chain,
                continuationContext: continuationContext,
                assets: referenceAssets,
                selectedReferencePath: selectedReferencePath,
                selectedReference: selectedReference,
                isLoadingAssets: isLoadingAssets,
                onSelectReference: onSelectReference,
                onRefreshAssets: onRefreshAssets,
                assetsErrorMessage: assetsErrorMessage,
              ),
            ];

            if (stacked) {
              return Column(
                children: [cards[0], const SizedBox(height: 16), cards[1]],
              );
            }

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: cards[0]),
                const SizedBox(width: 16),
                Expanded(child: cards[1]),
              ],
            );
          },
        ),
        const SizedBox(height: 16),
        GlassCard(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              IncidentCardHeader(
                accent: AppColors.cta,
                icon: Icons.analytics_rounded,
                title: '资产对比与漂移检测',
                subtitle: '基于最近资产选择基线，针对关键数值字段运行 PSI 漂移检测，决定是否需要重新训练或继续监控。',
                workspaceLabel:
                    continuationContext?.workspaceTargetLabel ??
                    chain?.workspaceTargetLabel,
                cardLabel:
                    continuationContext?.cardTargetLabel ??
                    chain?.cardTargetLabel,
                incidentLabel:
                    continuationContext?.incidentTargetLabel ??
                    chain?.incidentTargetLabel,
                summary:
                    continuationContext?.workspaceBrief ??
                    chain?.workspaceBrief,
              ),
              const SizedBox(height: 16),
              Text('检测字段', style: AppTextStyles.labelLarge),
              const SizedBox(height: 8),
              if (availableFeatures.isEmpty)
                Text(
                  '当前结果缺少可用于漂移检测的数值字段。请先生成带数值 schema 的资产。',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                )
              else
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: availableFeatures
                      .map(
                        (feature) => FilterChip(
                          label: Text(feature),
                          selected: selectedFeatures.contains(feature),
                          onSelected: (_) => onToggleFeature(feature),
                        ),
                      )
                      .toList(growable: false),
                ),
              const SizedBox(height: 16),
              WorkspaceInlineActionBar(
                actions: [
                  WorkspaceActionLaneAction(
                    label: isRunningDrift ? '检测中...' : '运行漂移检测',
                    icon: Icons.analytics_rounded,
                    onTap: canRunDrift ? onRunDrift : null,
                    tone: WorkspaceActionLaneTone.primary,
                    isLoading: isRunningDrift,
                  ),
                  WorkspaceActionLaneAction(
                    label: '复制漂移报告',
                    icon: Icons.content_copy_rounded,
                    onTap: report == null ? null : onCopyDriftReport,
                  ),
                ],
              ),
              if (driftErrorMessage != null) ...[
                const SizedBox(height: 12),
                Text(
                  driftErrorMessage!,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.error,
                  ),
                ),
              ],
              if (report != null) ...[
                const SizedBox(height: 16),
                _DriftReportSummaryCard(
                  highlighted: focusArea == 'report',
                  report: report!,
                  selectedReference: selectedReference,
                  currentQualityScore: currentQualityScore,
                ),
                const SizedBox(height: 16),
                _GovernanceDecisionCard(
                  highlighted: focusArea == 'decision',
                  report: report!,
                  selectedReference: selectedReference,
                  currentQualityScore: currentQualityScore,
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _CurrentAssetCard extends StatelessWidget {
  const _CurrentAssetCard({
    required this.highlighted,
    this.chain,
    this.continuationContext,
    required this.currentAssetLabel,
    required this.currentStoragePath,
    required this.currentQualityScore,
    required this.onCopyCurrentPath,
  });

  final bool highlighted;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;
  final String currentAssetLabel;
  final String? currentStoragePath;
  final double? currentQualityScore;
  final VoidCallback onCopyCurrentPath;

  @override
  Widget build(BuildContext context) {
    final hasPath =
        currentStoragePath != null && currentStoragePath!.isNotEmpty;
    final card = GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IncidentCardHeader(
            accent: AppColors.primary,
            icon: Icons.inventory_2_rounded,
            title: '当前资产',
            subtitle: currentAssetLabel,
            trailing: highlighted
                ? WorkspaceStatusChip(
                    label:
                        continuationContext?.cardTargetLabel ??
                        chain?.cardTargetLabel ??
                        '当前资产',
                    icon: Icons.dashboard_customize_rounded,
                    foreground: AppColors.primary,
                    background: AppColors.primary.withValues(alpha: 0.12),
                  )
                : null,
            workspaceLabel: highlighted
                ? continuationContext?.workspaceTargetLabel ??
                      chain?.workspaceTargetLabel
                : null,
            cardLabel: highlighted
                ? continuationContext?.cardTargetLabel ?? chain?.cardTargetLabel
                : null,
            incidentLabel: highlighted
                ? continuationContext?.incidentTargetLabel ??
                      chain?.incidentTargetLabel
                : null,
            summary: highlighted
                ? continuationContext?.workspaceBrief ?? chain?.workspaceBrief
                : null,
          ),
          const SizedBox(height: 8),
          _DigestRow(label: '资产标签', value: currentAssetLabel),
          const SizedBox(height: 8),
          _DigestRow(
            label: '质量评分',
            value: currentQualityScore == null
                ? '--'
                : '${currentQualityScore!.toStringAsFixed(0)} / 100',
          ),
          const SizedBox(height: 8),
          Text('Storage Path', style: AppTextStyles.labelMedium),
          const SizedBox(height: 6),
          SelectableText(
            hasPath ? currentStoragePath! : '当前结果尚未归档为可比较资产',
            style: AppTextStyles.bodySmall.copyWith(
              color: hasPath ? AppColors.textPrimary : AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 12),
          WorkspaceInlineActionBar(
            actions: [
              WorkspaceActionLaneAction(
                label: '复制当前路径',
                icon: Icons.copy_rounded,
                onTap: hasPath ? onCopyCurrentPath : null,
              ),
            ],
          ),
        ],
      ),
    );
    return _highlightShell(
      highlighted: highlighted,
      color: AppColors.primary,
      child: card,
    );
  }
}

class _ReferenceAssetCard extends StatelessWidget {
  const _ReferenceAssetCard({
    required this.highlighted,
    this.chain,
    this.continuationContext,
    required this.assets,
    required this.selectedReferencePath,
    required this.selectedReference,
    required this.isLoadingAssets,
    required this.onSelectReference,
    required this.onRefreshAssets,
    this.assetsErrorMessage,
  });

  final bool highlighted;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;
  final List<HistoryRecord> assets;
  final String? selectedReferencePath;
  final HistoryRecord? selectedReference;
  final bool isLoadingAssets;
  final ValueChanged<String?> onSelectReference;
  final VoidCallback onRefreshAssets;
  final String? assetsErrorMessage;

  @override
  Widget build(BuildContext context) {
    final card = GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IncidentCardHeader(
            accent: AppColors.warning,
            icon: Icons.compare_arrows_rounded,
            title: '基线资产',
            subtitle: selectedReference == null
                ? '选择一个历史资产作为漂移对比基线。'
                : _assetLabel(selectedReference!),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (highlighted)
                  WorkspaceStatusChip(
                    label:
                        continuationContext?.cardTargetLabel ??
                        chain?.cardTargetLabel ??
                        '选择基线',
                    icon: Icons.dashboard_customize_rounded,
                    foreground: AppColors.warning,
                    background: AppColors.warning.withValues(alpha: 0.12),
                  ),
                IconButton(
                  onPressed: isLoadingAssets ? null : onRefreshAssets,
                  icon: const Icon(Icons.refresh_rounded),
                  tooltip: '刷新资产列表',
                ),
              ],
            ),
            workspaceLabel: highlighted
                ? continuationContext?.workspaceTargetLabel ??
                      chain?.workspaceTargetLabel
                : null,
            cardLabel: highlighted
                ? continuationContext?.cardTargetLabel ?? chain?.cardTargetLabel
                : null,
            incidentLabel: highlighted
                ? continuationContext?.incidentTargetLabel ??
                      chain?.incidentTargetLabel
                : null,
            summary: highlighted
                ? continuationContext?.workspaceBrief ?? chain?.workspaceBrief
                : null,
          ),
          const SizedBox(height: 8),
          if (assets.isEmpty)
            Text(
              assetsErrorMessage ?? '暂无可用历史资产。需要至少一个已归档的数据分析结果作为基线。',
              style: AppTextStyles.bodySmall.copyWith(
                color: assetsErrorMessage == null
                    ? AppColors.textSecondary
                    : AppColors.error,
              ),
            )
          else ...[
            DropdownButtonFormField<String>(
              initialValue: selectedReferencePath,
              decoration: const InputDecoration(labelText: 'Reference Asset'),
              items: assets
                  .map(
                    (asset) => DropdownMenuItem<String>(
                      value: asset.storageUrl,
                      child: Text(_assetLabel(asset)),
                    ),
                  )
                  .toList(growable: false),
              onChanged: isLoadingAssets ? null : onSelectReference,
            ),
            if (selectedReference != null) ...[
              const SizedBox(height: 12),
              _DigestRow(label: '文件名', value: selectedReference!.filename),
              const SizedBox(height: 8),
              _DigestRow(
                label: '质量评分',
                value: selectedReference!.qualityScore == null
                    ? '--'
                    : '${selectedReference!.qualityScore!.toStringAsFixed(0)} / 100',
              ),
              const SizedBox(height: 8),
              _DigestRow(
                label: '创建时间',
                value: selectedReference!.createdAt == null
                    ? '--'
                    : DateFormat(
                        'MM-dd HH:mm',
                      ).format(selectedReference!.createdAt!.toLocal()),
              ),
            ],
          ],
        ],
      ),
    );
    return _highlightShell(
      highlighted: highlighted,
      color: AppColors.warning,
      child: card,
    );
  }
}

class _DriftReportSummaryCard extends StatelessWidget {
  const _DriftReportSummaryCard({
    required this.highlighted,
    required this.report,
    required this.selectedReference,
    required this.currentQualityScore,
  });

  final bool highlighted;
  final DataDriftReport report;
  final HistoryRecord? selectedReference;
  final double? currentQualityScore;

  @override
  Widget build(BuildContext context) {
    final statusTone = switch (report.overallStatus) {
      'drift' => (AppColors.error, AppColors.error.withValues(alpha: 0.08)),
      'warning' => (
        AppColors.warning,
        AppColors.warning.withValues(alpha: 0.12),
      ),
      _ => (AppColors.success, AppColors.successLight),
    };
    final qualityDelta =
        (currentQualityScore != null && selectedReference?.qualityScore != null)
        ? currentQualityScore! - selectedReference!.qualityScore!
        : null;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: statusTone.$2,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: highlighted
            ? Border.all(
                color: statusTone.$1.withValues(alpha: 0.22),
                width: 1.2,
              )
            : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _SummaryChip(
                label: '整体状态',
                value: report.overallStatus.toUpperCase(),
                color: statusTone.$1,
              ),
              _SummaryChip(
                label: '稳定',
                value: '${report.summary.stable}',
                color: AppColors.success,
              ),
              _SummaryChip(
                label: '警告',
                value: '${report.summary.warning}',
                color: AppColors.warning,
              ),
              _SummaryChip(
                label: '漂移',
                value: '${report.summary.drift}',
                color: AppColors.error,
              ),
              if (qualityDelta != null)
                _SummaryChip(
                  label: '质量差值',
                  value:
                      '${qualityDelta >= 0 ? '+' : ''}${qualityDelta.toStringAsFixed(1)}',
                  color: qualityDelta >= 0
                      ? AppColors.success
                      : AppColors.error,
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(report.recommendation, style: AppTextStyles.bodyMedium),
          const SizedBox(height: 12),
          if (report.features.isEmpty)
            Text(
              '当前未返回特征级结果。',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            )
          else
            Column(
              children: report.features
                  .take(5)
                  .map(
                    (feature) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _FeatureDriftRow(feature: feature),
                    ),
                  )
                  .toList(growable: false),
            ),
        ],
      ),
    );
  }
}

class _FeatureDriftRow extends StatelessWidget {
  const _FeatureDriftRow({required this.feature});

  final FeatureDriftStat feature;

  @override
  Widget build(BuildContext context) {
    final tone = switch (feature.status) {
      'drift' => AppColors.error,
      'warning' => AppColors.warning,
      _ => AppColors.success,
    };
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Row(
        children: [
          Expanded(
            flex: 3,
            child: Text(feature.name, style: AppTextStyles.labelLarge),
          ),
          Expanded(
            child: Text(
              'PSI ${feature.psi.toStringAsFixed(3)}',
              style: AppTextStyles.labelMedium.copyWith(color: tone),
            ),
          ),
          Expanded(
            child: Text(
              'mean ${feature.meanShift >= 0 ? '+' : ''}${feature.meanShift.toStringAsFixed(2)}',
              style: AppTextStyles.bodySmall,
            ),
          ),
          Expanded(
            child: Text(
              feature.status.toUpperCase(),
              textAlign: TextAlign.end,
              style: AppTextStyles.labelMedium.copyWith(color: tone),
            ),
          ),
        ],
      ),
    );
  }
}

class _GovernanceDecisionCard extends StatelessWidget {
  const _GovernanceDecisionCard({
    required this.highlighted,
    required this.report,
    required this.selectedReference,
    required this.currentQualityScore,
  });

  final bool highlighted;
  final DataDriftReport report;
  final HistoryRecord? selectedReference;
  final double? currentQualityScore;

  @override
  Widget build(BuildContext context) {
    final decision = _governanceDecision(
      report: report,
      selectedReference: selectedReference,
      currentQualityScore: currentQualityScore,
    );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: decision.color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(
          color: decision.color.withValues(alpha: highlighted ? 0.28 : 0.16),
          width: highlighted ? 1.3 : 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(decision.icon, size: 18, color: decision.color),
              const SizedBox(width: 8),
              Expanded(child: Text('治理结论', style: AppTextStyles.h4)),
              _SummaryChip(
                label: '建议',
                value: decision.label,
                color: decision.color,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(decision.message, style: AppTextStyles.bodyMedium),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _SummaryChip(
                label: '基线',
                value: selectedReference?.filename ?? '未选择',
                color: AppColors.primary,
              ),
              _SummaryChip(
                label: '状态',
                value: report.overallStatus.toUpperCase(),
                color: decision.color,
              ),
              if (decision.qualityDeltaLabel != null)
                _SummaryChip(
                  label: '质量差值',
                  value: decision.qualityDeltaLabel!,
                  color: decision.qualityDelta! >= 0
                      ? AppColors.success
                      : AppColors.error,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

String _focusArea(
  AssetChainSummary? chain, {
  WorkbenchLaunchContext? continuationContext,
  required bool hasCurrentAsset,
  required bool hasReference,
  required bool hasReport,
}) {
  switch (continuationContext?.cardTarget ?? chain?.cardTarget) {
    case 'current_asset':
      return 'current';
    case 'reference_asset':
      return 'reference';
    case 'drift_report':
      return 'report';
    case 'governance_decision':
      return 'decision';
  }
  if (!hasCurrentAsset || chain?.status == 'action') {
    return 'current';
  }
  if (!hasReference) {
    return 'reference';
  }
  if (hasReport && (chain?.status == 'incident' || chain?.status == 'watch')) {
    return 'decision';
  }
  if (hasReport) {
    return 'report';
  }
  return 'reference';
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

class _DigestRow extends StatelessWidget {
  const _DigestRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 88,
          child: Text(label, style: AppTextStyles.labelMedium),
        ),
        Expanded(child: Text(value, style: AppTextStyles.bodyMedium)),
      ],
    );
  }
}

class _SummaryChip extends StatelessWidget {
  const _SummaryChip({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        '$label · $value',
        style: AppTextStyles.labelMedium.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

String _assetLabel(HistoryRecord asset) {
  final createdAt = asset.createdAt == null
      ? '--'
      : DateFormat('MM-dd HH:mm').format(asset.createdAt!.toLocal());
  return '${asset.filename} · $createdAt';
}

class _GovernanceDecision {
  const _GovernanceDecision({
    required this.label,
    required this.message,
    required this.color,
    required this.icon,
    this.qualityDelta,
  });

  final String label;
  final String message;
  final Color color;
  final IconData icon;
  final double? qualityDelta;

  String? get qualityDeltaLabel {
    final value = qualityDelta;
    if (value == null) {
      return null;
    }
    return '${value >= 0 ? '+' : ''}${value.toStringAsFixed(1)}';
  }
}

_GovernanceDecision _governanceDecision({
  required DataDriftReport report,
  required HistoryRecord? selectedReference,
  required double? currentQualityScore,
}) {
  final referenceQuality = selectedReference?.qualityScore;
  final qualityDelta = (referenceQuality != null && currentQualityScore != null)
      ? currentQualityScore - referenceQuality
      : null;

  switch (report.overallStatus) {
    case 'drift':
      return _GovernanceDecision(
        label: '建议重训',
        message: '当前资产相对基线已出现明显漂移。建议暂停直接复用，优先重新训练模型或重建知识库，再继续下游流程。',
        color: AppColors.error,
        icon: Icons.restart_alt_rounded,
        qualityDelta: qualityDelta,
      );
    case 'warning':
      return _GovernanceDecision(
        label: '加强监控',
        message: '当前资产与基线存在可观差异，尚未达到强制重训阈值。建议继续监控，并在进入训练或知识库前复核关键字段。',
        color: AppColors.warning,
        icon: Icons.visibility_rounded,
        qualityDelta: qualityDelta,
      );
    default:
      return _GovernanceDecision(
        label: '可继续复用',
        message: '当前资产相对基线保持稳定，可继续进入训练、知识库构建或后续分析链路。',
        color: AppColors.success,
        icon: Icons.verified_rounded,
        qualityDelta: qualityDelta,
      );
  }
}
