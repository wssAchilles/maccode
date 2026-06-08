/// 历史与审计资产台账
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/ai_lab_launch_intent.dart';
import '../../models/data_analysis_launch_intent.dart';
import '../../models/history_record.dart';
import '../../models/job_record.dart';
import '../../models/optimization_launch_intent.dart';
import '../../models/dashboard_summary.dart';
import '../../utils/asset_chain_context.dart';
import '../../utils/external_link.dart';
import '../common/glass_card.dart';
import '../operations/duty_section_block.dart';
import '../operations/incident_card_header.dart';
import '../operations/workspace_action_lane.dart';

class HistoryAssetLedger extends StatelessWidget {
  const HistoryAssetLedger({
    super.key,
    required this.jobs,
    required this.records,
    this.assetSummary,
    this.dutySummary,
    this.alerts = const <DashboardAlert>[],
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
  });

  final List<JobRecord> jobs;
  final List<HistoryRecord> records;
  final AssetSummary? assetSummary;
  final DutySummary? dutySummary;
  final List<DashboardAlert> alerts;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;

  @override
  Widget build(BuildContext context) {
    final datasetAssets = records
        .where(
          (record) =>
              record.summary != null ||
              (record.storageUrl?.isNotEmpty ?? false),
        )
        .take(4)
        .toList(growable: false);
    final modelAssets = jobs
        .where(
          (job) =>
              job.type == 'ml_train' &&
              job.status == 'succeeded' &&
              (job.result['model_path']?.toString().isNotEmpty ?? false),
        )
        .take(4)
        .toList(growable: false);
    final knowledgeAssets = jobs
        .where(
          (job) =>
              job.type == 'rag_ingest' &&
              job.status == 'succeeded' &&
              (_firstString([
                    job.result['collection'],
                    job.input['collection_name'],
                  ])?.isNotEmpty ??
                  false),
        )
        .take(4)
        .toList(growable: false);
    final optimizationAssets = jobs
        .where(
          (job) =>
              job.type == 'optimization' &&
              job.status == 'succeeded' &&
              job.result.isNotEmpty,
        )
        .take(4)
        .toList(growable: false);
    final datasetChain = findChainSummary(assetSummary, 'dataset');
    final modelChain = findChainSummary(assetSummary, 'model');
    final knowledgeChain = findChainSummary(assetSummary, 'knowledge');
    final optimizationChain = findChainSummary(assetSummary, 'optimization');
    final assetAlerts = alerts
        .where((alert) => (alert.assetKey ?? '').isNotEmpty)
        .toList(growable: false);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (assetAlerts.isNotEmpty) ...[
          _AssetRiskStrip(
            alerts: assetAlerts,
            assetSummary: assetSummary,
            onOpenAiLab: onOpenAiLab,
            onOpenDataAnalysis: onOpenDataAnalysis,
            onOpenOptimization: onOpenOptimization,
          ),
          const SizedBox(height: 16),
        ],
        _buildInventoryStrip(
          datasetCount:
              assetSummary?.inventory.datasetAssets ?? datasetAssets.length,
          modelCount: assetSummary?.inventory.modelAssets ?? modelAssets.length,
          knowledgeCount:
              assetSummary?.inventory.knowledgeAssets ?? knowledgeAssets.length,
          optimizationCount:
              assetSummary?.inventory.optimizationAssets ??
              optimizationAssets.length,
        ),
        const SizedBox(height: 16),
        if (assetSummary != null) ...[
          _CompactLedgerMatrix(
            summary: assetSummary!,
            dutySummary: dutySummary,
            datasetReplayCount: datasetAssets.length,
            modelReplayCount: modelAssets.length,
            knowledgeReplayCount: knowledgeAssets.length,
            optimizationReplayCount: optimizationAssets.length,
            onOpenAiLab: onOpenAiLab,
            onOpenDataAnalysis: onOpenDataAnalysis,
            onOpenOptimization: onOpenOptimization,
          ),
          const SizedBox(height: 16),
        ],
        LayoutBuilder(
          builder: (context, constraints) {
            final stacked = constraints.maxWidth < 1180;
            final panels = [
              _LedgerPanel(
                title: '数据资产台账',
                description: '保留分析结果、质量评分和可继续治理的存储路径。',
                accent: AppColors.primary,
                icon: Icons.dataset_rounded,
                emptyMessage: '暂无可治理的数据资产。',
                children: datasetAssets
                    .map(
                      (record) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _DatasetLedgerTile(
                          record: record,
                          chain: datasetChain,
                          onOpenAiLab: onOpenAiLab,
                          onOpenDataAnalysis: onOpenDataAnalysis,
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
              _LedgerPanel(
                title: '模型资产台账',
                description: '训练产物的来源、目标列、指标和回填入口都固定在同一视图。',
                accent: AppColors.cta,
                icon: Icons.model_training_rounded,
                emptyMessage: '暂无成功训练产物。',
                children: modelAssets
                    .map(
                      (job) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _ModelLedgerTile(
                          job: job,
                          chain: modelChain,
                          onOpenAiLab: onOpenAiLab,
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
              _LedgerPanel(
                title: '知识库资产台账',
                description: '集合名、文档来源和索引规模集中展示，方便继续治理和问答复盘。',
                accent: AppColors.success,
                icon: Icons.account_tree_rounded,
                emptyMessage: '暂无成功知识库快照。',
                children: knowledgeAssets
                    .map(
                      (job) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _KnowledgeLedgerTile(
                          job: job,
                          chain: knowledgeChain,
                          onOpenAiLab: onOpenAiLab,
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
              _LedgerPanel(
                title: '优化结果台账',
                description: '保留场景参数和最近节省结果，便于回看 What-If 推演。',
                accent: AppColors.warning,
                icon: Icons.bolt_rounded,
                emptyMessage: '暂无可回放的优化结果。',
                children: optimizationAssets
                    .map(
                      (job) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _OptimizationLedgerTile(
                          job: job,
                          chain: optimizationChain,
                          onOpenOptimization: onOpenOptimization,
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
            ];

            if (stacked) {
              return Column(
                children: [
                  for (var i = 0; i < panels.length; i++) ...[
                    panels[i],
                    if (i < panels.length - 1) const SizedBox(height: 16),
                  ],
                ],
              );
            }

            return Column(
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: panels[0]),
                    const SizedBox(width: 16),
                    Expanded(child: panels[1]),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: panels[2]),
                    const SizedBox(width: 16),
                    Expanded(child: panels[3]),
                  ],
                ),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildInventoryStrip({
    required int datasetCount,
    required int modelCount,
    required int knowledgeCount,
    required int optimizationCount,
  }) {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        _LedgerInventoryChip(
          label: '数据资产',
          value: '$datasetCount',
          icon: Icons.dataset_rounded,
          color: AppColors.primary,
        ),
        _LedgerInventoryChip(
          label: '模型产物',
          value: '$modelCount',
          icon: Icons.model_training_rounded,
          color: AppColors.cta,
        ),
        _LedgerInventoryChip(
          label: '知识快照',
          value: '$knowledgeCount',
          icon: Icons.account_tree_rounded,
          color: AppColors.success,
        ),
        _LedgerInventoryChip(
          label: '优化结果',
          value: '$optimizationCount',
          icon: Icons.bolt_rounded,
          color: AppColors.warning,
        ),
      ],
    );
  }
}

class _CompactLedgerMatrix extends StatelessWidget {
  const _CompactLedgerMatrix({
    required this.summary,
    this.dutySummary,
    required this.datasetReplayCount,
    required this.modelReplayCount,
    required this.knowledgeReplayCount,
    required this.optimizationReplayCount,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
  });

  final AssetSummary summary;
  final DutySummary? dutySummary;
  final int datasetReplayCount;
  final int modelReplayCount;
  final int knowledgeReplayCount;
  final int optimizationReplayCount;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;

  @override
  Widget build(BuildContext context) {
    final rows =
        summary.chainSummaries
            .map((chain) {
              final replayCount = switch (chain.key) {
                'dataset' => datasetReplayCount,
                'model' => modelReplayCount,
                'knowledge' => knowledgeReplayCount,
                'optimization' => optimizationReplayCount,
                _ => 0,
              };
              return _CompactLedgerRow(
                chain: chain,
                isDutyFocus: isDutyFocusChain(chain, dutySummary),
                replayCount: replayCount,
                onOpenAiLab: onOpenAiLab,
                onOpenDataAnalysis: onOpenDataAnalysis,
                onOpenOptimization: onOpenOptimization,
              );
            })
            .toList(growable: false)
          ..sort(
            (a, b) => compareChainsByDutyFocus(a.chain, b.chain, dutySummary),
          );

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: DutySectionBlock(
        title: '资产台账矩阵',
        subtitle: '用更高密度的方式统一查看链路状态、版本、焦点、责任和回放库存，减少在四类资产卡片之间来回切换。',
        child: Column(
          children: [
            for (var i = 0; i < rows.length; i++) ...[
              rows[i],
              if (i < rows.length - 1) const SizedBox(height: 10),
            ],
          ],
        ),
      ),
    );
  }
}

class _CompactLedgerRow extends StatelessWidget {
  const _CompactLedgerRow({
    required this.chain,
    required this.isDutyFocus,
    required this.replayCount,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
  });

  final AssetChainSummary chain;
  final bool isDutyFocus;
  final int replayCount;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;

  @override
  Widget build(BuildContext context) {
    final tone = _matrixTone(chain);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: chain.status == 'healthy'
            ? AppColors.surfaceVariant
            : Color.alphaBlend(
                tone.withValues(alpha: 0.06),
                AppColors.surfaceVariant,
              ),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(
          color: tone.withValues(
            alpha: chain.isOverdue || chain.status != 'healthy' ? 0.28 : 0.16,
          ),
          width: chain.isOverdue ? 1.4 : 1,
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 920;
          final summary = _rowSummary(context);
          final action = _rowAction();
          final actionWidgets = action == null
              ? const <Widget>[]
              : <Widget>[action];
          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [summary, const SizedBox(height: 10), ...actionWidgets],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: summary),
              const SizedBox(width: 16),
              ...actionWidgets,
            ],
          );
        },
      ),
    );
  }

  Widget _rowSummary(BuildContext context) {
    final tone = _matrixTone(chain);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _LedgerTag(label: chain.label, color: _matrixTone(chain)),
            _LedgerTag(
              label: chain.statusLabel,
              color: chain.isOverdue ? AppColors.error : AppColors.primary,
            ),
            if (isDutyFocus)
              const _LedgerTag(label: '值班焦点', color: AppColors.primary),
            _LedgerTag(label: chain.workspaceTargetLabel, color: tone),
            _LedgerTag(label: chain.cardTargetLabel, color: tone),
            _LedgerTag(label: chain.incidentTargetLabel, color: tone),
            if (chain.isOverdue)
              _LedgerTag(
                label: '超时 ${chain.overdueMinutes}m',
                color: AppColors.error,
              ),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          'v${chain.latestVersion} · ${chain.latestLabel}',
          style: AppTextStyles.labelLarge,
        ),
        const SizedBox(height: 6),
        Text(
          buildChainWorkspaceSummary(chain, includeWorkspaceLabel: true),
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 10),
        _MatrixFocusBand(chain: chain, replayCount: replayCount, accent: tone),
        const SizedBox(height: 10),
        _MatrixFactTable(
          rows: [
            _MatrixFactRowData(
              label: '当前焦点',
              value:
                  '${chain.dispositionTargetLabel} · ${buildChainWorkspaceSummary(chain)}',
              highlighted: _matrixHighlight(chain) == _MatrixFocusArea.focus,
            ),
            _MatrixFactRowData(
              label: 'SLA',
              value:
                  '${chain.escalationStateLabel} · ${chain.isOverdue ? '超时 ${chain.overdueMinutes}m' : '已运行 ${chain.elapsedMinutes}m'}',
              highlighted: _matrixHighlight(chain) == _MatrixFocusArea.sla,
            ),
            _MatrixFactRowData(
              label: '回放',
              value: '$replayCount 条可回放 · ${chain.actionLabel}',
              highlighted: _matrixHighlight(chain) == _MatrixFocusArea.replay,
            ),
            _MatrixFactRowData(
              label: 'Active Job',
              value: _matrixJobSummary(chain),
              highlighted: _matrixHighlight(chain) == _MatrixFocusArea.job,
            ),
            _MatrixFactRowData(
              label: 'Failure / Lineage',
              value: _matrixFailureOrLineage(chain),
              highlighted: _matrixHighlight(chain) == _MatrixFocusArea.failure,
            ),
            _MatrixFactRowData(label: 'Owner', value: chain.ownerLabel),
            _MatrixFactRowData(
              label: 'Target',
              value:
                  '${chain.workspaceTargetLabel} / ${chain.cardTargetLabel} / ${chain.incidentTargetLabel}',
            ),
            _MatrixFactRowData(label: 'Lineage', value: chain.lineageSummary),
          ],
          accent: tone,
        ),
      ],
    );
  }

  Widget? _rowAction() {
    final context = buildLaunchContextFromChain(chain, prefix: '资产台账矩阵');
    final sourceLabel = buildChainSourceLabel(
      chain,
      prefix: '资产台账矩阵',
      includeWorkspaceBrief: true,
    );
    switch (chain.key) {
      case 'dataset':
        if (onOpenDataAnalysis == null) {
          return null;
        }
        return FilledButton.tonalIcon(
          onPressed: () => onOpenDataAnalysis!(
            DataAnalysisLaunchIntent.workspace(
              sourceLabel: sourceLabel,
              context: context,
            ),
          ),
          icon: const Icon(Icons.analytics_rounded),
          label: Text(chain.actionLabel),
        );
      case 'model':
        if (onOpenAiLab == null) {
          return null;
        }
        return FilledButton.tonalIcon(
          onPressed: () => onOpenAiLab!(
            AiLabLaunchIntent.deepLearning(
              '',
              sourceLabel: sourceLabel,
              context: context,
            ),
          ),
          icon: const Icon(Icons.model_training_rounded),
          label: Text(chain.actionLabel),
        );
      case 'knowledge':
        if (onOpenAiLab == null) {
          return null;
        }
        return FilledButton.tonalIcon(
          onPressed: () => onOpenAiLab!(
            AiLabLaunchIntent.rag(
              '',
              sourceLabel: sourceLabel,
              context: context,
            ),
          ),
          icon: const Icon(Icons.account_tree_rounded),
          label: Text(chain.actionLabel),
        );
      case 'optimization':
        if (onOpenOptimization == null) {
          return null;
        }
        return FilledButton.tonalIcon(
          onPressed: () => onOpenOptimization!(
            OptimizationLaunchIntent(
              sourceLabel: sourceLabel,
              context: context,
            ),
          ),
          icon: const Icon(Icons.bolt_rounded),
          label: Text(chain.actionLabel),
        );
      default:
        return null;
    }
  }
}

class _MatrixFocusBand extends StatelessWidget {
  const _MatrixFocusBand({
    required this.chain,
    required this.replayCount,
    required this.accent,
  });

  final AssetChainSummary chain;
  final int replayCount;
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
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Current disposition',
                  style: AppTextStyles.labelMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  _matrixDispositionSummary(chain, replayCount),
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textPrimary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          _LedgerTag(label: chain.dispositionTargetLabel, color: accent),
        ],
      ),
    );
  }
}

class _MatrixFactRowData {
  const _MatrixFactRowData({
    required this.label,
    required this.value,
    this.highlighted = false,
  });

  final String label;
  final String value;
  final bool highlighted;
}

class _MatrixFactTable extends StatelessWidget {
  const _MatrixFactTable({required this.rows, required this.accent});

  final List<_MatrixFactRowData> rows;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.1)),
      ),
      child: Column(
        children: [
          for (var index = 0; index < rows.length; index++) ...[
            _MatrixFactRow(row: rows[index], accent: accent),
            if (index < rows.length - 1)
              const Divider(height: 1, color: AppColors.border),
          ],
        ],
      ),
    );
  }
}

class _MatrixFactRow extends StatelessWidget {
  const _MatrixFactRow({required this.row, required this.accent});

  final _MatrixFactRowData row;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      child: Row(
        children: [
          SizedBox(
            width: 128,
            child: Text(
              row.label,
              style: AppTextStyles.labelMedium.copyWith(
                color: row.highlighted ? accent : AppColors.textSecondary,
                fontWeight: row.highlighted ? FontWeight.w700 : null,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              row.value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTextStyles.bodySmall.copyWith(
                color: row.highlighted
                    ? AppColors.textPrimary
                    : AppColors.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LedgerTag extends StatelessWidget {
  const _LedgerTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelMedium.copyWith(color: color),
      ),
    );
  }
}

Color _matrixTone(AssetChainSummary chain) {
  if (chain.isOverdue || chain.status == 'incident') {
    return AppColors.error;
  }
  if (chain.escalationTier > 0 || chain.status == 'active') {
    return AppColors.warning;
  }
  switch (chain.key) {
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

enum _MatrixFocusArea { focus, sla, replay, failure, job }

_MatrixFocusArea _matrixHighlight(AssetChainSummary chain) {
  switch (chain.dispositionTarget) {
    case 'sla':
      return _MatrixFocusArea.sla;
    case 'replay':
      return _MatrixFocusArea.replay;
    case 'failure':
      return _MatrixFocusArea.failure;
    case 'job':
      return _MatrixFocusArea.job;
    case 'governance':
    case 'focus':
    default:
      return _MatrixFocusArea.focus;
  }
}

String _matrixDispositionSummary(AssetChainSummary chain, int replayCount) {
  switch (chain.dispositionTarget) {
    case 'sla':
      return '${chain.escalationStateLabel} · ${chain.isOverdue ? '超时 ${chain.overdueMinutes}m' : '已运行 ${chain.elapsedMinutes}m'}';
    case 'replay':
      return '$replayCount 条可回放资产 · ${buildChainWorkspaceSummary(chain)}';
    case 'failure':
      return _matrixFailureOrLineage(chain);
    case 'job':
      return _matrixJobSummary(chain);
    case 'governance':
    case 'focus':
    default:
      return chain.incidentBrief;
  }
}

String _matrixJobSummary(AssetChainSummary chain) {
  if (chain.jobStatus == '--') {
    return 'No active job';
  }
  return '${chain.jobStatus} · ${chain.jobPhase} · ${chain.jobProgress}%';
}

String _matrixFailureOrLineage(AssetChainSummary chain) {
  if (chain.failureSource != '--') {
    return '${chain.failurePhase} · ${chain.failureSource}';
  }
  return chain.lineageSummary;
}

class _AssetRiskStrip extends StatelessWidget {
  const _AssetRiskStrip({
    required this.alerts,
    this.assetSummary,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
  });

  final List<DashboardAlert> alerts;
  final AssetSummary? assetSummary;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;

  @override
  Widget build(BuildContext context) {
    return DutySectionBlock(
      title: '资产风险联动',
      subtitle: '把概览页发现的资产缺口直接落到台账入口，并给出对应工作台的处理动作。',
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        children: alerts
            .map(
              (alert) => SizedBox(
                width: 320,
                child: _AssetRiskCard(
                  alert: alert,
                  chain: findChainSummary(assetSummary, alert.assetKey ?? ''),
                  onOpenAiLab: onOpenAiLab,
                  onOpenDataAnalysis: onOpenDataAnalysis,
                  onOpenOptimization: onOpenOptimization,
                ),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _AssetRiskCard extends StatelessWidget {
  const _AssetRiskCard({
    required this.alert,
    this.chain,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
  });

  final DashboardAlert alert;
  final AssetChainSummary? chain;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;

  @override
  Widget build(BuildContext context) {
    final tone = _riskTone(alert.severity);
    final action = _riskAction(
      alert.assetKey,
      chain: chain,
      onOpenAiLab: onOpenAiLab,
      onOpenDataAnalysis: onOpenDataAnalysis,
      onOpenOptimization: onOpenOptimization,
    );

    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IncidentCardHeader(
            accent: tone.color,
            icon: tone.icon,
            title: alert.title,
            subtitle: alert.message,
            trailing: WorkspaceStatusChip(
              label: alert.severity.toUpperCase(),
              icon: tone.icon,
              foreground: tone.color,
              background: tone.color.withValues(alpha: 0.12),
            ),
          ),
          if (action != null) ...[
            const SizedBox(height: 12),
            WorkspaceInlineActionBar(
              actions: [
                WorkspaceActionLaneAction(
                  label: action.label,
                  icon: action.icon,
                  onTap: action.onTap,
                  tone: WorkspaceActionLaneTone.tonal,
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _RiskAction {
  const _RiskAction({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
}

class _RiskTone {
  const _RiskTone({required this.color, required this.icon});

  final Color color;
  final IconData icon;
}

_RiskTone _riskTone(String severity) {
  switch (severity) {
    case 'error':
      return const _RiskTone(color: AppColors.error, icon: Icons.error_outline);
    case 'warning':
      return const _RiskTone(
        color: AppColors.warning,
        icon: Icons.warning_amber_rounded,
      );
    default:
      return const _RiskTone(
        color: AppColors.primary,
        icon: Icons.info_outline,
      );
  }
}

_RiskAction? _riskAction(
  String? assetKey, {
  AssetChainSummary? chain,
  ValueChanged<AiLabLaunchIntent>? onOpenAiLab,
  ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis,
  ValueChanged<OptimizationLaunchIntent>? onOpenOptimization,
}) {
  final context = buildLaunchContextFromChain(chain, prefix: '资产风险联动');
  final sourceLabel = buildChainSourceLabel(
    chain,
    prefix: '资产风险联动',
    includeWorkspaceBrief: true,
  );
  switch (assetKey) {
    case 'dataset':
      if (onOpenDataAnalysis == null) {
        return null;
      }
      return _RiskAction(
        label: '打开数据分析工作台',
        icon: Icons.analytics_rounded,
        onTap: () => onOpenDataAnalysis(
          DataAnalysisLaunchIntent.workspace(
            sourceLabel: sourceLabel,
            context: context,
          ),
        ),
      );
    case 'model':
      if (onOpenAiLab == null) {
        return null;
      }
      return _RiskAction(
        label: '打开训练工作台',
        icon: Icons.model_training_rounded,
        onTap: () => onOpenAiLab(
          AiLabLaunchIntent.deepLearning(
            '',
            sourceLabel: sourceLabel,
            context: context,
          ),
        ),
      );
    case 'knowledge':
      if (onOpenAiLab == null) {
        return null;
      }
      return _RiskAction(
        label: '打开知识库工作台',
        icon: Icons.account_tree_rounded,
        onTap: () => onOpenAiLab(
          AiLabLaunchIntent.rag('', sourceLabel: sourceLabel, context: context),
        ),
      );
    case 'optimization':
      if (onOpenOptimization == null) {
        return null;
      }
      return _RiskAction(
        label: '打开优化工作台',
        icon: Icons.bolt_rounded,
        onTap: () => onOpenOptimization(
          OptimizationLaunchIntent(sourceLabel: sourceLabel, context: context),
        ),
      );
    default:
      return null;
  }
}

class _LedgerPanel extends StatelessWidget {
  const _LedgerPanel({
    required this.title,
    required this.description,
    required this.accent,
    required this.icon,
    required this.emptyMessage,
    required this.children,
  });

  final String title;
  final String description;
  final Color accent;
  final IconData icon;
  final String emptyMessage;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IncidentCardHeader(
            accent: accent,
            icon: icon,
            title: title,
            subtitle: description,
          ),
          const SizedBox(height: 14),
          if (children.isEmpty)
            Text(emptyMessage, style: AppTextStyles.bodySmall)
          else
            ...children,
        ],
      ),
    );
  }
}

class _LedgerInventoryChip extends StatelessWidget {
  const _LedgerInventoryChip({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Text(label, style: AppTextStyles.labelMedium),
          const SizedBox(width: 10),
          Text(value, style: AppTextStyles.labelLarge.copyWith(color: color)),
        ],
      ),
    );
  }
}

class _DatasetLedgerTile extends StatelessWidget {
  const _DatasetLedgerTile({
    required this.record,
    this.chain,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
  });

  final HistoryRecord record;
  final AssetChainSummary? chain;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;

  @override
  Widget build(BuildContext context) {
    final replayContext = buildLaunchContext(
      sourceLabel: '数据资产台账',
      chain: chain,
      workspaceTarget: 'data_governance',
      cardTarget: 'current_asset',
      incidentTarget: 'asset',
      workspaceBrief: '数据资产已载入当前资产',
      watchSummary: '优先核对当前资产质量与结果摘要',
    );
    final replaySourceLabel = buildWorkbenchSourceLabel(
      replayContext,
      prefix: '数据资产台账',
    );
    final trainingContext = buildLaunchContext(
      sourceLabel: '数据资产台账',
      chain: chain,
      workspaceTarget: 'ai_runtime',
      cardTarget: 'runtime_product',
      incidentTarget: 'runtime',
      workspaceBrief: '数据资产已送入训练入口',
      watchSummary: '优先核对训练配置和目标列',
    );
    final trainingSourceLabel = buildWorkbenchSourceLabel(
      trainingContext,
      prefix: '数据资产台账',
    );
    final score = record.qualityScore == null
        ? '未评分'
        : record.qualityScore!.toStringAsFixed(1);
    final rows = record.basicInfo?['rows']?.toString() ?? '--';
    final columns = record.basicInfo?['columns']?.toString() ?? '--';

    return _LedgerTile(
      accent: AppColors.primary,
      title: record.filename,
      subtitle:
          'quality=$score · rows=$rows · cols=$columns · ${_formatTime(record.createdAt)}',
      metaRows: [
        _LedgerMetaRow(label: '存储路径', value: record.storageUrl ?? '未归档'),
        _LedgerMetaRow(label: '来源链路', value: 'CSV -> Analysis -> Asset'),
      ],
      recommendedActionKey: _recommendedDatasetLedgerAction(
        chain,
        canReplayAnalysis: onOpenDataAnalysis != null && record.summary != null,
        canSendTraining:
            onOpenAiLab != null && (record.storageUrl?.isNotEmpty ?? false),
      ),
      actions: [
        if (onOpenDataAnalysis != null && record.summary != null)
          WorkspaceActionLaneAction(
            label: '回放分析',
            icon: Icons.analytics_rounded,
            semanticKey: 'replay_analysis',
            onTap: () => onOpenDataAnalysis!(
              DataAnalysisLaunchIntent.fromHistoryRecord(
                record,
                sourceLabel: replaySourceLabel,
                context: replayContext,
              ),
            ),
            tone: WorkspaceActionLaneTone.tonal,
          ),
        if (onOpenAiLab != null && (record.storageUrl?.isNotEmpty ?? false))
          WorkspaceActionLaneAction(
            label: '送入训练',
            icon: Icons.model_training_rounded,
            semanticKey: 'send_training',
            onTap: () => onOpenAiLab!(
              AiLabLaunchIntent.fromHistoryRecordForTraining(
                record,
                sourceLabel: trainingSourceLabel,
                context: trainingContext,
              ),
            ),
          ),
      ],
    );
  }
}

class _ModelLedgerTile extends StatelessWidget {
  const _ModelLedgerTile({required this.job, this.chain, this.onOpenAiLab});

  final JobRecord job;
  final AssetChainSummary? chain;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;

  @override
  Widget build(BuildContext context) {
    final launchContext = buildLaunchContext(
      sourceLabel: '模型资产台账',
      chain: chain,
      workspaceTarget: 'ai_runtime',
      cardTarget: 'runtime_product',
      incidentTarget: 'runtime',
      workspaceBrief: '模型资产已回填到训练入口',
      watchSummary: '优先核对训练配置与最新模型产物',
    );
    final sourceLabel = buildWorkbenchSourceLabel(
      launchContext,
      prefix: '模型资产台账',
    );
    final modelPath = job.result['model_path']?.toString() ?? '--';
    final modelType = job.result['model_type']?.toString() ?? 'model';
    final targetColumn =
        _firstString([
          job.result['target_column'],
          job.input['target_column'],
        ]) ??
        '--';
    final storagePath = _firstString([job.input['storage_path']]) ?? '--';
    final backendLabel = job.isVertexTraining
        ? 'Vertex AI'
        : 'Cloud Run Legacy';
    final vertexState = _vertexStateLabel(job.externalJobState);
    final vertexConsoleUrl = job.externalJobConsoleUrl;

    return _LedgerTile(
      accent: AppColors.cta,
      title: 'v${_versionFor(job)} · ${modelType.toUpperCase()}',
      subtitle:
          'job=${job.jobId.substring(0, 8)} · 尝试 ${job.attemptCount}/${job.maxAttempts} · ${_formatTime(job.completedAt)}',
      metaRows: [
        _LedgerMetaRow(label: '模型路径', value: modelPath),
        _LedgerMetaRow(label: '来源数据', value: storagePath),
        _LedgerMetaRow(label: '目标列', value: targetColumn),
        _LedgerMetaRow(label: '训练后端', value: backendLabel),
        if (vertexState != null)
          _LedgerMetaRow(label: '平台状态', value: vertexState),
        _LedgerMetaRow(
          label: '来源链路',
          value: 'Dataset -> Sequence -> Train -> Artifact',
        ),
      ],
      recommendedActionKey: 'apply_model_asset',
      actions: [
        if (onOpenAiLab != null)
          WorkspaceActionLaneAction(
            label: '回填训练入口',
            icon: Icons.restart_alt_rounded,
            semanticKey: 'apply_model_asset',
            onTap: () => onOpenAiLab!(
              AiLabLaunchIntent.fromTrainingJob(
                job,
                sourceLabel: sourceLabel,
                context: launchContext,
              ),
            ),
            tone: WorkspaceActionLaneTone.tonal,
          ),
        if ((vertexConsoleUrl ?? '').isNotEmpty)
          WorkspaceActionLaneAction(
            label: '打开 Vertex 作业',
            icon: Icons.open_in_new_rounded,
            semanticKey: 'open_vertex_job',
            onTap: () {
              if (vertexConsoleUrl != null) {
                openExternalLink(vertexConsoleUrl);
              }
            },
            tone: WorkspaceActionLaneTone.outline,
          ),
      ],
    );
  }
}

class _KnowledgeLedgerTile extends StatelessWidget {
  const _KnowledgeLedgerTile({required this.job, this.chain, this.onOpenAiLab});

  final JobRecord job;
  final AssetChainSummary? chain;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;

  @override
  Widget build(BuildContext context) {
    final launchContext = buildLaunchContext(
      sourceLabel: '知识库资产台账',
      chain: chain,
      workspaceTarget: 'ai_runtime',
      cardTarget: 'runtime_product',
      incidentTarget: 'runtime',
      workspaceBrief: '知识快照已回填到知识入口',
      watchSummary: '优先核对集合配置和最新知识快照',
    );
    final sourceLabel = buildWorkbenchSourceLabel(
      launchContext,
      prefix: '知识库资产台账',
    );
    final collection =
        _firstString([
          job.result['collection'],
          job.input['collection_name'],
        ]) ??
        'default';
    final storagePath =
        _firstString([job.result['storage_path'], job.input['storage_path']]) ??
        '--';
    final count = job.result['count']?.toString() ?? '--';
    final reset = _asBool(job.input['reset']) == true ? '重建' : '增量';

    return _LedgerTile(
      accent: AppColors.success,
      title: 'v${_versionFor(job)} · $collection',
      subtitle:
          'job=${job.jobId.substring(0, 8)} · $reset 模式 · ${_formatTime(job.completedAt)}',
      metaRows: [
        _LedgerMetaRow(label: '文档来源', value: storagePath),
        _LedgerMetaRow(label: '片段规模', value: count),
        _LedgerMetaRow(
          label: '最近阶段',
          value: job.latestEvent?.phase ?? 'packaging',
        ),
        _LedgerMetaRow(
          label: '来源链路',
          value: 'Docs -> Parse -> Embed -> Collection',
        ),
      ],
      recommendedActionKey: 'apply_knowledge_asset',
      actions: [
        if (onOpenAiLab != null)
          WorkspaceActionLaneAction(
            label: '回填知识入口',
            icon: Icons.hub_rounded,
            semanticKey: 'apply_knowledge_asset',
            onTap: () => onOpenAiLab!(
              AiLabLaunchIntent.fromRagJob(
                job,
                sourceLabel: sourceLabel,
                context: launchContext,
              ),
            ),
            tone: WorkspaceActionLaneTone.tonal,
          ),
      ],
    );
  }
}

class _OptimizationLedgerTile extends StatelessWidget {
  const _OptimizationLedgerTile({
    required this.job,
    this.chain,
    this.onOpenOptimization,
  });

  final JobRecord job;
  final AssetChainSummary? chain;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;

  @override
  Widget build(BuildContext context) {
    final launchContext = buildLaunchContext(
      sourceLabel: '优化资产台账',
      chain: chain,
      workspaceTarget: 'optimization_registry',
      cardTarget: 'latest_snapshot',
      incidentTarget: 'asset',
      workspaceBrief: '优化快照已载入结果工作台',
      watchSummary: '优先核对最新快照与结果摘要',
    );
    final sourceLabel = buildWorkbenchSourceLabel(
      launchContext,
      prefix: '优化资产台账',
    );
    final targetDate = job.input['target_date']?.toString() ?? '--';
    final initialSoc = job.input['initial_soc']?.toString() ?? '--';
    final optimization = job.result['optimization'];
    String savings = '--';
    if (optimization is Map) {
      final summary = optimization['summary'];
      if (summary is Map && summary['savings'] != null) {
        savings = summary['savings'].toString();
      }
    }

    return _LedgerTile(
      accent: AppColors.warning,
      title: 'v${_versionFor(job)} · ${job.displayTitle}',
      subtitle:
          'job=${job.jobId.substring(0, 8)} · target=$targetDate · ${_formatTime(job.completedAt)}',
      metaRows: [
        _LedgerMetaRow(label: '初始 SOC', value: initialSoc),
        _LedgerMetaRow(
          label: '节省结果',
          value: savings == '--' ? '--' : '$savings 元',
        ),
        _LedgerMetaRow(
          label: '来源链路',
          value: 'Scenario -> Forecast -> Solver -> Strategy',
        ),
      ],
      recommendedActionKey: 'replay_optimization',
      actions: [
        if (onOpenOptimization != null)
          WorkspaceActionLaneAction(
            label: '回放优化',
            icon: Icons.bolt_rounded,
            semanticKey: 'replay_optimization',
            onTap: () => onOpenOptimization!(
              OptimizationLaunchIntent.fromJob(
                job,
                sourceLabel: sourceLabel,
                context: launchContext,
              ),
            ),
            tone: WorkspaceActionLaneTone.tonal,
          ),
      ],
    );
  }
}

class _LedgerTile extends StatelessWidget {
  const _LedgerTile({
    required this.accent,
    required this.title,
    required this.subtitle,
    required this.metaRows,
    this.recommendedActionKey,
    required this.actions,
  });

  final Color accent;
  final String title;
  final String subtitle;
  final List<_LedgerMetaRow> metaRows;
  final String? recommendedActionKey;
  final List<WorkspaceActionLaneAction> actions;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTextStyles.labelLarge),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 12),
          for (var i = 0; i < metaRows.length; i++) ...[
            _LedgerInfoRow(row: metaRows[i]),
            if (i < metaRows.length - 1) const SizedBox(height: 8),
          ],
          if (actions.isNotEmpty) ...[
            const SizedBox(height: 12),
            WorkspaceInlineActionBar(
              recommendedActionKey: recommendedActionKey,
              actions: actions,
            ),
          ],
        ],
      ),
    );
  }
}

String? _recommendedDatasetLedgerAction(
  AssetChainSummary? chain, {
  required bool canReplayAnalysis,
  required bool canSendTraining,
}) {
  final cardTarget = chain?.cardTarget;
  if (cardTarget == 'current_asset' ||
      cardTarget == 'schema_topology' ||
      cardTarget == 'field_distribution' ||
      cardTarget == 'risk_digest' ||
      cardTarget == 'next_actions' ||
      cardTarget == 'drift_report' ||
      cardTarget == 'governance_decision') {
    if (canReplayAnalysis) {
      return 'replay_analysis';
    }
  }
  if (cardTarget == 'runtime_product' || cardTarget == 'registry_snapshot') {
    if (canSendTraining) {
      return 'send_training';
    }
  }
  if (canReplayAnalysis) {
    return 'replay_analysis';
  }
  if (canSendTraining) {
    return 'send_training';
  }
  return null;
}

class _LedgerMetaRow {
  const _LedgerMetaRow({required this.label, required this.value});

  final String label;
  final String value;
}

class _LedgerInfoRow extends StatelessWidget {
  const _LedgerInfoRow({required this.row});

  final _LedgerMetaRow row;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 72,
          child: Text(
            row.label,
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(child: Text(row.value, style: AppTextStyles.bodySmall)),
      ],
    );
  }
}

String _versionFor(JobRecord job) {
  final timestamp = job.completedAt ?? job.submittedAt;
  if (timestamp == null) {
    return job.jobId.substring(0, 6);
  }
  return DateFormat('MMdd-HHmm').format(timestamp.toLocal());
}

String _formatTime(DateTime? value) {
  if (value == null) {
    return '--';
  }
  return DateFormat('MM-dd HH:mm').format(value.toLocal());
}

String? _vertexStateLabel(String? value) {
  switch (value) {
    case 'JOB_STATE_QUEUED':
      return '排队中';
    case 'JOB_STATE_PENDING':
      return '资源准备中';
    case 'JOB_STATE_RUNNING':
      return '训练中';
    case 'JOB_STATE_SUCCEEDED':
      return '已完成';
    case 'JOB_STATE_FAILED':
      return '失败';
    case 'JOB_STATE_CANCELLED':
      return '已取消';
    case 'JOB_STATE_CANCELLING':
      return '取消中';
    case null:
      return null;
    default:
      return value;
  }
}

String? _firstString(List<Object?> values) {
  for (final value in values) {
    if (value is String && value.isNotEmpty) {
      return value;
    }
  }
  return null;
}

bool? _asBool(Object? value) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    final normalized = value.toLowerCase();
    if (normalized == 'true' || normalized == '1') {
      return true;
    }
    if (normalized == 'false' || normalized == '0') {
      return false;
    }
  }
  return null;
}
