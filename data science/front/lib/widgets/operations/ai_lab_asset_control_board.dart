/// AI Lab 产物与知识库治理板
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/dashboard_summary.dart';
import '../../models/job_record.dart';
import '../../models/workbench_launch_context.dart';
import '../common/glass_card.dart';
import 'asset_chain_section_header.dart';
import 'incident_card_header.dart';
import 'workspace_action_lane.dart';

class AiLabAssetControlBoard extends StatelessWidget {
  const AiLabAssetControlBoard({
    super.key,
    this.activeChain,
    this.continuationContext,
    this.assetSummary,
    required this.trainingJobs,
    required this.ragJobs,
    required this.onApplyTrainingArtifact,
    required this.onCopyModelPath,
    required this.onApplyKnowledgeSnapshot,
    required this.onCopyCollection,
    required this.onClearConversation,
    required this.onApplyModelAsset,
    required this.onCopyModelPassport,
    required this.onApplyKnowledgeAsset,
    required this.onCopyKnowledgePassport,
  });

  final AssetChainSummary? activeChain;
  final WorkbenchLaunchContext? continuationContext;
  final AssetSummary? assetSummary;
  final List<JobRecord> trainingJobs;
  final List<JobRecord> ragJobs;
  final ValueChanged<JobRecord> onApplyTrainingArtifact;
  final ValueChanged<String> onCopyModelPath;
  final ValueChanged<JobRecord> onApplyKnowledgeSnapshot;
  final ValueChanged<String> onCopyCollection;
  final VoidCallback onClearConversation;
  final ValueChanged<AssetModel> onApplyModelAsset;
  final ValueChanged<AssetModel> onCopyModelPassport;
  final ValueChanged<KnowledgeAsset> onApplyKnowledgeAsset;
  final ValueChanged<KnowledgeAsset> onCopyKnowledgePassport;

  @override
  Widget build(BuildContext context) {
    final trainingArtifacts = trainingJobs
        .where(
          (job) =>
              job.status == 'succeeded' &&
              (job.result['model_path']?.toString().isNotEmpty ?? false),
        )
        .take(3)
        .toList(growable: false);
    final knowledgeSnapshots = ragJobs
        .where(
          (job) =>
              job.status == 'succeeded' &&
              ((job.result['collection']?.toString().isNotEmpty ?? false) ||
                  (job.input['collection_name']?.toString().isNotEmpty ??
                      false)),
        )
        .take(3)
        .toList(growable: false);
    final latestModelAsset = assetSummary?.models.isNotEmpty == true
        ? assetSummary!.models.first
        : null;
    final latestKnowledgeAsset = assetSummary?.knowledgeBases.isNotEmpty == true
        ? assetSummary!.knowledgeBases.first
        : null;

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1180;
        final inventory = _AssetInventorySummary(
          trainingCount:
              assetSummary?.inventory.modelAssets ?? trainingArtifacts.length,
          knowledgeCount:
              assetSummary?.inventory.knowledgeAssets ??
              knowledgeSnapshots.length,
          latestTrainingVersion:
              latestModelAsset?.version ??
              (trainingArtifacts.isEmpty
                  ? '--'
                  : _versionFor(trainingArtifacts.first)),
          latestKnowledgeVersion:
              latestKnowledgeAsset?.version ??
              (knowledgeSnapshots.isEmpty
                  ? '--'
                  : _versionFor(knowledgeSnapshots.first)),
        );
        final hasRegistrySnapshots =
            latestModelAsset != null || latestKnowledgeAsset != null;
        final hasVersionTimeline =
            (assetSummary?.models.isNotEmpty ?? false) ||
            (assetSummary?.knowledgeBases.isNotEmpty ?? false);
        final runtimeFocus =
            activeChain?.workspaceTarget == 'ai_runtime' ||
            activeChain?.sectionTarget == 'ai_lab_runtime';
        final runtimeCardFocused =
            continuationContext?.cardTarget == 'runtime_product' ||
            activeChain?.cardTarget == 'runtime_product' ||
            runtimeFocus;
        final timelineCardFocused =
            continuationContext?.cardTarget == 'version_timeline' ||
            activeChain?.cardTarget == 'version_timeline';
        final registryCardFocused =
            continuationContext?.cardTarget == 'registry_snapshot' ||
            activeChain?.cardTarget == 'registry_snapshot';
        final panels = [
          _ArtifactPanel(
            title: '最近训练任务产物',
            description: '运行期产物保留训练配置、指标和尝试次数，用来快速回填或核查最近执行。',
            icon: Icons.inventory_2_rounded,
            accent: AppColors.cta,
            workspaceLabel: runtimeCardFocused && activeChain?.key == 'model'
                ? continuationContext?.workspaceTargetLabel ??
                      activeChain?.workspaceTargetLabel
                : null,
            highlighted: runtimeCardFocused && activeChain?.key == 'model',
            cardLabel: runtimeCardFocused && activeChain?.key == 'model'
                ? continuationContext?.cardTargetLabel ??
                      activeChain?.cardTargetLabel
                : null,
            incidentLabel: runtimeCardFocused && activeChain?.key == 'model'
                ? continuationContext?.incidentTargetLabel ??
                      activeChain?.incidentTargetLabel
                : null,
            summary: runtimeCardFocused && activeChain?.key == 'model'
                ? continuationContext?.workspaceBrief ??
                      activeChain?.workspaceBrief
                : null,
            emptyMessage: '暂无已完成训练产物。提交训练任务后，这里会出现可回填的模型资产。',
            footer: null,
            children: trainingArtifacts
                .map(
                  (job) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _TrainingArtifactTile(
                      job: job,
                      onApply: () => onApplyTrainingArtifact(job),
                      onCopyPath: () => onCopyModelPath(
                        job.result['model_path']?.toString() ?? '',
                      ),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
          _ArtifactPanel(
            title: '最近知识库任务产物',
            description: '最近成功构建的集合、文档规模和来源路径集中在这里，便于回填和问答治理。',
            icon: Icons.account_tree_rounded,
            accent: AppColors.primary,
            workspaceLabel: runtimeCardFocused && activeChain?.key == 'knowledge'
                ? continuationContext?.workspaceTargetLabel ??
                      activeChain?.workspaceTargetLabel
                : null,
            highlighted: runtimeCardFocused && activeChain?.key == 'knowledge',
            cardLabel: runtimeCardFocused && activeChain?.key == 'knowledge'
                ? continuationContext?.cardTargetLabel ??
                      activeChain?.cardTargetLabel
                : null,
            incidentLabel: runtimeCardFocused && activeChain?.key == 'knowledge'
                ? continuationContext?.incidentTargetLabel ??
                      activeChain?.incidentTargetLabel
                : null,
            summary: runtimeCardFocused && activeChain?.key == 'knowledge'
                ? continuationContext?.workspaceBrief ??
                      activeChain?.workspaceBrief
                : null,
            emptyMessage: '暂无成功的知识库构建结果。提供文档路径后即可生成可复用快照。',
            footer: Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: onClearConversation,
                icon: const Icon(Icons.layers_clear_rounded),
                label: const Text('清空问答会话'),
              ),
            ),
            children: knowledgeSnapshots
                .map(
                  (job) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _KnowledgeSnapshotTile(
                      job: job,
                      onApply: () => onApplyKnowledgeSnapshot(job),
                      onCopyCollection: () =>
                          onCopyCollection(_collectionForJob(job)),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ];

        return Column(
          children: [
            AssetChainSectionHeader(
              title: '资产治理板',
              subtitle: '把注册表快照、版本轨迹和最近任务产物放到同一资产面，减少训练与知识快照之间的切换成本。',
              chain: activeChain,
              icon: Icons.inventory_2_rounded,
            ),
            const SizedBox(height: 16),
            inventory,
            if (hasRegistrySnapshots) ...[
              const SizedBox(height: 16),
              _RegistrySnapshotSection(
                activeChain: activeChain,
                highlighted: registryCardFocused,
                latestModelAsset: latestModelAsset,
                latestKnowledgeAsset: latestKnowledgeAsset,
                continuationContext: continuationContext,
                onApplyModelAsset: onApplyModelAsset,
                onCopyModelPath: onCopyModelPath,
                onCopyModelPassport: onCopyModelPassport,
                onApplyKnowledgeAsset: onApplyKnowledgeAsset,
                onCopyCollection: onCopyCollection,
                onCopyKnowledgePassport: onCopyKnowledgePassport,
              ),
            ],
            if (hasVersionTimeline) ...[
              const SizedBox(height: 16),
              _AiLabVersionTimelineSection(
                summary: assetSummary!,
                activeChain: activeChain,
                highlighted: timelineCardFocused,
                continuationContext: continuationContext,
              ),
            ],
            const SizedBox(height: 16),
            if (compact)
              Column(
                children: [
                  for (var i = 0; i < panels.length; i++) ...[
                    panels[i],
                    if (i < panels.length - 1) const SizedBox(height: 16),
                  ],
                ],
              )
            else
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: panels[0]),
                  const SizedBox(width: 16),
                  Expanded(child: panels[1]),
                ],
              ),
          ],
        );
      },
    );
  }
}

class _AiLabVersionTimelineSection extends StatelessWidget {
  const _AiLabVersionTimelineSection({
    required this.summary,
    required this.activeChain,
    this.highlighted = false,
    this.continuationContext,
  });

  final AssetSummary summary;
  final AssetChainSummary? activeChain;
  final bool highlighted;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final lanes = [
      _VersionLane(
        title: '模型版本轨迹',
        description: '按统一资产摘要查看最近模型版本和来源数据。',
        accent: AppColors.cta,
        icon: Icons.model_training_rounded,
        workspaceLabel: highlighted && activeChain?.key == 'model'
            ? continuationContext?.workspaceTargetLabel ??
                  activeChain?.workspaceTargetLabel
            : null,
        highlighted: highlighted && activeChain?.key == 'model',
        cardLabel: activeChain?.key == 'model'
            ? continuationContext?.cardTargetLabel ?? activeChain?.cardTargetLabel
            : null,
        incidentLabel: highlighted && activeChain?.key == 'model'
            ? continuationContext?.incidentTargetLabel ??
                  activeChain?.incidentTargetLabel
            : null,
        summary: highlighted && activeChain?.key == 'model'
            ? continuationContext?.workspaceBrief ?? activeChain?.workspaceBrief
            : null,
        items: summary.models
            .take(3)
            .map(
              (asset) => _VersionItem(
                version: asset.version,
                headline:
                    '${(asset.modelType ?? 'model').toUpperCase()} / ${asset.targetColumn ?? '--'}',
                supporting:
                    'source=${asset.storagePath ?? '--'} · path=${asset.modelPath ?? '--'}',
              ),
            )
            .toList(growable: false),
      ),
      _VersionLane(
        title: '知识快照轨迹',
        description: '按统一资产摘要查看最近知识集合版本和索引模式。',
        accent: AppColors.primary,
        icon: Icons.account_tree_rounded,
        workspaceLabel: highlighted && activeChain?.key == 'knowledge'
            ? continuationContext?.workspaceTargetLabel ??
                  activeChain?.workspaceTargetLabel
            : null,
        highlighted: highlighted && activeChain?.key == 'knowledge',
        cardLabel: activeChain?.key == 'knowledge'
            ? continuationContext?.cardTargetLabel ?? activeChain?.cardTargetLabel
            : null,
        incidentLabel: highlighted && activeChain?.key == 'knowledge'
            ? continuationContext?.incidentTargetLabel ??
                  activeChain?.incidentTargetLabel
            : null,
        summary: highlighted && activeChain?.key == 'knowledge'
            ? continuationContext?.workspaceBrief ?? activeChain?.workspaceBrief
            : null,
        items: summary.knowledgeBases
            .take(3)
            .map(
              (asset) => _VersionItem(
                version: asset.version,
                headline: asset.collection ?? 'default',
                supporting:
                    '${asset.reset == true ? 'reset' : 'incremental'} · docs=${asset.count ?? '--'} · source=${asset.storagePath ?? '--'}',
              ),
            )
            .toList(growable: false),
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1120;
        if (compact) {
          return Column(
            children: [
              for (var i = 0; i < lanes.length; i++) ...[
                lanes[i],
                if (i < lanes.length - 1) const SizedBox(height: 16),
              ],
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: lanes[0]),
            const SizedBox(width: 16),
            Expanded(child: lanes[1]),
          ],
        );
      },
    );
  }
}

class _VersionLane extends StatelessWidget {
  const _VersionLane({
    required this.title,
    required this.description,
    required this.accent,
    required this.icon,
    this.workspaceLabel,
    this.highlighted = false,
    this.cardLabel,
    this.incidentLabel,
    this.summary,
    required this.items,
  });

  final String title;
  final String description;
  final Color accent;
  final IconData icon;
  final String? workspaceLabel;
  final bool highlighted;
  final String? cardLabel;
  final String? incidentLabel;
  final String? summary;
  final List<_VersionItem> items;

  @override
  Widget build(BuildContext context) {
    final card = GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IncidentCardHeader(
            accent: accent,
            icon: icon,
            title: title,
            subtitle: description,
            trailing: highlighted && cardLabel != null
                ? WorkspaceStatusChip(
                    label: cardLabel!,
                    icon: Icons.dashboard_customize_rounded,
                    foreground: accent,
                    background: accent.withValues(alpha: 0.12),
                  )
                : null,
            workspaceLabel: highlighted ? workspaceLabel : null,
            cardLabel: highlighted ? cardLabel : null,
            incidentLabel: highlighted ? incidentLabel : null,
            summary: highlighted ? summary : null,
          ),
          const SizedBox(height: 14),
          if (items.isEmpty)
            Text('暂无版本轨迹。', style: AppTextStyles.bodySmall)
          else
            ...items.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _VersionTile(item: item, accent: accent),
              ),
            ),
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

class _VersionItem {
  const _VersionItem({
    required this.version,
    required this.headline,
    required this.supporting,
  });

  final String version;
  final String headline;
  final String supporting;
}

class _VersionTile extends StatelessWidget {
  const _VersionTile({required this.item, required this.accent});

  final _VersionItem item;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return _AssetTileContainer(
      accent: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ToneChip(label: 'v${item.version}', color: accent),
          const SizedBox(height: 10),
          Text(item.headline, style: AppTextStyles.labelLarge),
          const SizedBox(height: 6),
          Text(
            item.supporting,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _RegistrySnapshotSection extends StatelessWidget {
  const _RegistrySnapshotSection({
    required this.activeChain,
    this.highlighted = false,
    this.continuationContext,
    required this.latestModelAsset,
    required this.latestKnowledgeAsset,
    required this.onApplyModelAsset,
    required this.onCopyModelPath,
    required this.onCopyModelPassport,
    required this.onApplyKnowledgeAsset,
    required this.onCopyCollection,
    required this.onCopyKnowledgePassport,
  });

  final AssetChainSummary? activeChain;
  final bool highlighted;
  final WorkbenchLaunchContext? continuationContext;
  final AssetModel? latestModelAsset;
  final KnowledgeAsset? latestKnowledgeAsset;
  final ValueChanged<AssetModel> onApplyModelAsset;
  final ValueChanged<String> onCopyModelPath;
  final ValueChanged<AssetModel> onCopyModelPassport;
  final ValueChanged<KnowledgeAsset> onApplyKnowledgeAsset;
  final ValueChanged<String> onCopyCollection;
  final ValueChanged<KnowledgeAsset> onCopyKnowledgePassport;

  @override
  Widget build(BuildContext context) {
    final cards = <Widget>[
      if (latestModelAsset != null)
        _RegistrySnapshotCard(
          title: '模型注册表快照',
          description: '统一资产摘要中的最新模型版本，用于版本治理、回填和交接。',
          accent: AppColors.cta,
          icon: Icons.model_training_rounded,
          workspaceLabel: highlighted && activeChain?.key == 'model'
              ? continuationContext?.workspaceTargetLabel ??
                    activeChain?.workspaceTargetLabel
              : null,
          highlighted: highlighted && activeChain?.key == 'model',
          cardLabel: activeChain?.key == 'model'
              ? continuationContext?.cardTargetLabel ?? activeChain?.cardTargetLabel
              : null,
          incidentLabel: highlighted && activeChain?.key == 'model'
              ? continuationContext?.incidentTargetLabel ??
                    activeChain?.incidentTargetLabel
              : null,
          summary: highlighted && activeChain?.key == 'model'
              ? continuationContext?.workspaceBrief ?? activeChain?.workspaceBrief
              : null,
          child: _ModelRegistryTile(
            asset: latestModelAsset!,
            onApply: () => onApplyModelAsset(latestModelAsset!),
            onCopyPath: () =>
                onCopyModelPath(latestModelAsset!.modelPath ?? ''),
            onCopyPassport: () => onCopyModelPassport(latestModelAsset!),
          ),
        ),
      if (latestKnowledgeAsset != null)
        _RegistrySnapshotCard(
          title: '知识注册表快照',
          description: '统一资产摘要中的最新知识集合版本，便于回放、问答和集合治理。',
          accent: AppColors.primary,
          icon: Icons.account_tree_rounded,
          workspaceLabel: highlighted && activeChain?.key == 'knowledge'
              ? continuationContext?.workspaceTargetLabel ??
                    activeChain?.workspaceTargetLabel
              : null,
          highlighted: highlighted && activeChain?.key == 'knowledge',
          cardLabel: activeChain?.key == 'knowledge'
              ? continuationContext?.cardTargetLabel ?? activeChain?.cardTargetLabel
              : null,
          incidentLabel: highlighted && activeChain?.key == 'knowledge'
              ? continuationContext?.incidentTargetLabel ??
                    activeChain?.incidentTargetLabel
              : null,
          summary: highlighted && activeChain?.key == 'knowledge'
              ? continuationContext?.workspaceBrief ?? activeChain?.workspaceBrief
              : null,
          child: _KnowledgeRegistryTile(
            asset: latestKnowledgeAsset!,
            onApply: () => onApplyKnowledgeAsset(latestKnowledgeAsset!),
            onCopyCollection: () =>
                onCopyCollection(latestKnowledgeAsset!.collection ?? ''),
            onCopyPassport: () =>
                onCopyKnowledgePassport(latestKnowledgeAsset!),
          ),
        ),
    ];

    if (cards.isEmpty) {
      return const SizedBox.shrink();
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1120 || cards.length == 1;
        if (compact) {
          return Column(
            children: [
              for (var i = 0; i < cards.length; i++) ...[
                cards[i],
                if (i < cards.length - 1) const SizedBox(height: 16),
              ],
            ],
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
    );
  }
}

class _RegistrySnapshotCard extends StatelessWidget {
  const _RegistrySnapshotCard({
    required this.title,
    required this.description,
    required this.accent,
    required this.icon,
    this.workspaceLabel,
    this.highlighted = false,
    this.cardLabel,
    this.incidentLabel,
    this.summary,
    required this.child,
  });

  final String title;
  final String description;
  final Color accent;
  final IconData icon;
  final String? workspaceLabel;
  final bool highlighted;
  final String? cardLabel;
  final String? incidentLabel;
  final String? summary;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final card = GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IncidentCardHeader(
            accent: accent,
            icon: icon,
            title: title,
            subtitle: description,
            trailing: highlighted && cardLabel != null
                ? WorkspaceStatusChip(
                    label: cardLabel!,
                    icon: Icons.dashboard_customize_rounded,
                    foreground: accent,
                    background: accent.withValues(alpha: 0.12),
                  )
                : null,
            workspaceLabel: highlighted ? workspaceLabel : null,
            cardLabel: highlighted ? cardLabel : null,
            incidentLabel: highlighted ? incidentLabel : null,
            summary: highlighted ? summary : null,
          ),
          const SizedBox(height: 14),
          child,
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

class _ModelRegistryTile extends StatelessWidget {
  const _ModelRegistryTile({
    required this.asset,
    required this.onApply,
    required this.onCopyPath,
    required this.onCopyPassport,
  });

  final AssetModel asset;
  final VoidCallback onApply;
  final VoidCallback onCopyPath;
  final VoidCallback onCopyPassport;

  @override
  Widget build(BuildContext context) {
    final modelType = (asset.modelType ?? 'model').toUpperCase();
    final completedAt = _formatCompletedAt(asset.completedAt);
    final lineage =
        'job=${asset.jobId.isEmpty ? '--' : asset.jobId.substring(0, asset.jobId.length < 8 ? asset.jobId.length : 8)} · '
        '尝试 ${asset.attemptCount ?? '--'}/${asset.maxAttempts ?? '--'}';

    return _AssetTileContainer(
      accent: AppColors.cta,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _ToneChip(label: 'v${asset.version}', color: AppColors.cta),
              _ToneChip(label: modelType, color: AppColors.primary),
              _ToneChip(label: completedAt, color: AppColors.success),
            ],
          ),
          const SizedBox(height: 12),
          _LabeledValue(
            label: '模型路径',
            value: asset.modelPath ?? '--',
            selectable: true,
          ),
          const SizedBox(height: 8),
          _LabeledValue(label: '训练数据', value: asset.storagePath ?? '--'),
          const SizedBox(height: 8),
          _LabeledValue(label: '目标列', value: asset.targetColumn ?? '--'),
          const SizedBox(height: 8),
          _LabeledValue(label: '资产血缘', value: lineage),
          const SizedBox(height: 12),
          WorkspaceInlineActionBar(
            actions: [
              WorkspaceActionLaneAction(
                label: '回填训练入口',
                icon: Icons.restart_alt_rounded,
                onTap: onApply,
                tone: WorkspaceActionLaneTone.primary,
              ),
              WorkspaceActionLaneAction(
                label: '复制模型路径',
                icon: Icons.copy_all_rounded,
                onTap: onCopyPath,
              ),
              WorkspaceActionLaneAction(
                label: '复制模型护照',
                icon: Icons.badge_rounded,
                onTap: onCopyPassport,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _KnowledgeRegistryTile extends StatelessWidget {
  const _KnowledgeRegistryTile({
    required this.asset,
    required this.onApply,
    required this.onCopyCollection,
    required this.onCopyPassport,
  });

  final KnowledgeAsset asset;
  final VoidCallback onApply;
  final VoidCallback onCopyCollection;
  final VoidCallback onCopyPassport;

  @override
  Widget build(BuildContext context) {
    final completedAt = _formatCompletedAt(asset.completedAt);
    final mode = asset.reset == true ? '重建索引' : '增量索引';
    final lineage =
        'job=${asset.jobId.isEmpty ? '--' : asset.jobId.substring(0, asset.jobId.length < 8 ? asset.jobId.length : 8)} · $mode';

    return _AssetTileContainer(
      accent: AppColors.primary,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _ToneChip(label: 'v${asset.version}', color: AppColors.primary),
              _ToneChip(
                label: asset.collection ?? 'default',
                color: AppColors.cta,
              ),
              _ToneChip(label: completedAt, color: AppColors.success),
            ],
          ),
          const SizedBox(height: 12),
          _LabeledValue(label: '文档来源', value: asset.storagePath ?? '--'),
          const SizedBox(height: 8),
          _LabeledValue(label: '文档片段数', value: '${asset.count ?? '--'}'),
          const SizedBox(height: 8),
          _LabeledValue(label: '治理模式', value: mode),
          const SizedBox(height: 8),
          _LabeledValue(label: '资产血缘', value: lineage),
          const SizedBox(height: 12),
          WorkspaceInlineActionBar(
            actions: [
              WorkspaceActionLaneAction(
                label: '回填知识入口',
                icon: Icons.hub_rounded,
                onTap: onApply,
                tone: WorkspaceActionLaneTone.primary,
              ),
              WorkspaceActionLaneAction(
                label: '复制集合名',
                icon: Icons.copy_rounded,
                onTap: onCopyCollection,
              ),
              WorkspaceActionLaneAction(
                label: '复制快照护照',
                icon: Icons.badge_rounded,
                onTap: onCopyPassport,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AssetInventorySummary extends StatelessWidget {
  const _AssetInventorySummary({
    required this.trainingCount,
    required this.knowledgeCount,
    required this.latestTrainingVersion,
    required this.latestKnowledgeVersion,
  });

  final int trainingCount;
  final int knowledgeCount;
  final String latestTrainingVersion;
  final String latestKnowledgeVersion;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        _InventoryChip(
          label: '训练版本',
          value: '$trainingCount',
          hint: '最新 v$latestTrainingVersion',
          icon: Icons.model_training_rounded,
          color: AppColors.cta,
        ),
        _InventoryChip(
          label: '知识快照',
          value: '$knowledgeCount',
          hint: '最新 v$latestKnowledgeVersion',
          icon: Icons.account_tree_rounded,
          color: AppColors.primary,
        ),
      ],
    );
  }
}

class _ArtifactPanel extends StatelessWidget {
  const _ArtifactPanel({
    required this.title,
    required this.description,
    required this.icon,
    required this.accent,
    this.workspaceLabel,
    this.highlighted = false,
    this.cardLabel,
    this.incidentLabel,
    this.summary,
    required this.emptyMessage,
    required this.children,
    this.footer,
  });

  final String title;
  final String description;
  final IconData icon;
  final Color accent;
  final String? workspaceLabel;
  final bool highlighted;
  final String? cardLabel;
  final String? incidentLabel;
  final String? summary;
  final String emptyMessage;
  final List<Widget> children;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    final card = GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IncidentCardHeader(
            accent: accent,
            icon: icon,
            title: title,
            subtitle: description,
            trailing: highlighted && cardLabel != null
                ? WorkspaceStatusChip(
                    label: cardLabel!,
                    icon: Icons.dashboard_customize_rounded,
                    foreground: accent,
                    background: accent.withValues(alpha: 0.12),
                  )
                : null,
            workspaceLabel: highlighted ? workspaceLabel : null,
            cardLabel: highlighted ? cardLabel : null,
            incidentLabel: highlighted ? incidentLabel : null,
            summary: highlighted ? summary : null,
          ),
          const SizedBox(height: 14),
          if (children.isEmpty)
            Text(emptyMessage, style: AppTextStyles.bodySmall)
          else
            ...children,
          if (footer != null) ...[const SizedBox(height: 4), footer!],
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

class _TrainingArtifactTile extends StatelessWidget {
  const _TrainingArtifactTile({
    required this.job,
    required this.onApply,
    required this.onCopyPath,
  });

  final JobRecord job;
  final VoidCallback onApply;
  final VoidCallback onCopyPath;

  @override
  Widget build(BuildContext context) {
    final modelType = job.result['model_type']?.toString() ?? 'model';
    final modelPath = job.result['model_path']?.toString() ?? '--';
    final storagePath = job.input['storage_path']?.toString() ?? '--';
    final targetColumn =
        job.result['target_column']?.toString() ??
        job.input['target_column']?.toString() ??
        '--';
    final completedAt = job.completedAt == null
        ? '--'
        : DateFormat('MM-dd HH:mm').format(job.completedAt!.toLocal());
    final metrics = job.result['metrics'];

    return _AssetTileContainer(
      accent: AppColors.cta,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _ToneChip(label: 'v${_versionFor(job)}', color: AppColors.cta),
              const SizedBox(width: 8),
              _ToneChip(
                label: modelType.toUpperCase(),
                color: AppColors.primary,
              ),
              const SizedBox(width: 8),
              _ToneChip(label: completedAt, color: AppColors.success),
            ],
          ),
          const SizedBox(height: 12),
          _LabeledValue(label: '模型路径', value: modelPath, selectable: true),
          const SizedBox(height: 8),
          _LabeledValue(label: '训练数据', value: storagePath),
          const SizedBox(height: 8),
          _LabeledValue(label: '目标列', value: targetColumn),
          const SizedBox(height: 8),
          _LabeledValue(
            label: '资产血缘',
            value:
                'job=${job.jobId.substring(0, 8)} · 尝试 ${job.attemptCount}/${job.maxAttempts}',
          ),
          if (metrics is Map && metrics.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: metrics.entries
                  .take(4)
                  .map(
                    (entry) => _MetricPill(
                      label: entry.key.toString(),
                      value: entry.value.toString(),
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
          const SizedBox(height: 12),
          WorkspaceInlineActionBar(
            actions: [
              WorkspaceActionLaneAction(
                label: '回填训练配置',
                icon: Icons.restart_alt_rounded,
                onTap: onApply,
                tone: WorkspaceActionLaneTone.primary,
              ),
              WorkspaceActionLaneAction(
                label: '复制模型路径',
                icon: Icons.copy_all_rounded,
                onTap: onCopyPath,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _KnowledgeSnapshotTile extends StatelessWidget {
  const _KnowledgeSnapshotTile({
    required this.job,
    required this.onApply,
    required this.onCopyCollection,
  });

  final JobRecord job;
  final VoidCallback onApply;
  final VoidCallback onCopyCollection;

  @override
  Widget build(BuildContext context) {
    final collection = _collectionForJob(job);
    final storagePath =
        job.result['storage_path']?.toString() ??
        job.input['storage_path']?.toString() ??
        '--';
    final count = job.result['count']?.toString() ?? '--';
    final latestStage = job.latestEvent?.message ?? job.statusMessage ?? '已完成';
    final completedAt = job.completedAt == null
        ? '--'
        : DateFormat('MM-dd HH:mm').format(job.completedAt!.toLocal());

    return _AssetTileContainer(
      accent: AppColors.primary,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _ToneChip(
                label: 'v${_versionFor(job)}',
                color: AppColors.primary,
              ),
              const SizedBox(width: 8),
              _ToneChip(label: collection, color: AppColors.cta),
              const SizedBox(width: 8),
              _ToneChip(label: completedAt, color: AppColors.success),
            ],
          ),
          const SizedBox(height: 12),
          _LabeledValue(label: '文档来源', value: storagePath),
          const SizedBox(height: 8),
          _LabeledValue(label: '文档片段数', value: count),
          const SizedBox(height: 8),
          _LabeledValue(label: '最近阶段', value: latestStage),
          const SizedBox(height: 8),
          _LabeledValue(
            label: '资产血缘',
            value:
                'job=${job.jobId.substring(0, 8)} · ${_asBool(job.input["reset"]) == true ? "重建" : "增量"} 索引',
          ),
          const SizedBox(height: 12),
          WorkspaceInlineActionBar(
            actions: [
              WorkspaceActionLaneAction(
                label: '回填知识库入口',
                icon: Icons.hub_rounded,
                onTap: onApply,
                tone: WorkspaceActionLaneTone.primary,
              ),
              WorkspaceActionLaneAction(
                label: '复制集合名',
                icon: Icons.copy_rounded,
                onTap: onCopyCollection,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AssetTileContainer extends StatelessWidget {
  const _AssetTileContainer({required this.child, required this.accent});

  final Widget child;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: child,
    );
  }
}

class _LabeledValue extends StatelessWidget {
  const _LabeledValue({
    required this.label,
    required this.value,
    this.selectable = false,
  });

  final String label;
  final String value;
  final bool selectable;

  @override
  Widget build(BuildContext context) {
    final text = selectable
        ? SelectableText(value, style: AppTextStyles.bodyMedium)
        : Text(value, style: AppTextStyles.bodyMedium);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTextStyles.labelMedium),
        const SizedBox(height: 4),
        text,
      ],
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: AppTextStyles.labelMedium),
          const SizedBox(width: 6),
          Text(
            value,
            style: AppTextStyles.labelLarge.copyWith(color: AppColors.primary),
          ),
        ],
      ),
    );
  }
}

class _ToneChip extends StatelessWidget {
  const _ToneChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelMedium.copyWith(color: color),
      ),
    );
  }
}

class _InventoryChip extends StatelessWidget {
  const _InventoryChip({
    required this.label,
    required this.value,
    required this.hint,
    required this.icon,
    required this.color,
  });

  final String label;
  final String value;
  final String hint;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: color.withValues(alpha: 0.16)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: AppTextStyles.labelMedium),
              const SizedBox(height: 2),
              Text(
                '$value · $hint',
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

String _collectionForJob(JobRecord job) {
  return job.result['collection']?.toString() ??
      job.input['collection_name']?.toString() ??
      'default';
}

String _versionFor(JobRecord job) {
  final timestamp = job.completedAt ?? job.submittedAt;
  if (timestamp == null) {
    return job.jobId.substring(0, 6);
  }
  return DateFormat('MMdd-HHmm').format(timestamp.toLocal());
}

String _formatCompletedAt(DateTime? value) {
  if (value == null) {
    return '--';
  }
  return DateFormat('MM-dd HH:mm').format(value.toLocal());
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
