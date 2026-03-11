/// 数据分析工作台组件
library;

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/analysis_result.dart';
import '../../models/dashboard_summary.dart';
import '../common/glass_card.dart';
import '../operations/embedded_page_header.dart';
import '../operations/metric_card.dart';
import 'data_analysis_state_views.dart';

class DataAnalysisWorkbenchHeader extends StatelessWidget {
  const DataAnalysisWorkbenchHeader({
    super.key,
    required this.currentUser,
    required this.pickedFile,
    required this.analysisResult,
    required this.saveToStorage,
    required this.latestStoragePath,
  });

  final User? currentUser;
  final PlatformFile? pickedFile;
  final AnalysisResult? analysisResult;
  final bool saveToStorage;
  final String? latestStoragePath;

  @override
  Widget build(BuildContext context) {
    final result = analysisResult;
    final qualityScore = result?.qualityAnalysis?.qualityScore;
    final highRiskCount = result?.qualityAnalysis?.highRiskColumns?.length ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        EmbeddedPageHeader(
          title: 'Data Analysis Workbench',
          description:
              '将认证、CSV 上传、质量审查、统计分析和 AI hand-off 收到同一工作台，减少页面跳转与上下文丢失。',
          badges: [
            EmbeddedHeaderBadge(
              label: '会话',
              value: currentUser == null ? '未登录' : '已连接',
              accent: currentUser == null
                  ? AppColors.warning
                  : AppColors.success,
              icon: currentUser == null
                  ? Icons.lock_outline_rounded
                  : Icons.verified_user_rounded,
            ),
            EmbeddedHeaderBadge(
              label: '数据集',
              value: pickedFile == null ? '未选择' : pickedFile!.name,
              accent: pickedFile == null
                  ? AppColors.textSecondary
                  : AppColors.primary,
              icon: pickedFile == null
                  ? Icons.upload_file_outlined
                  : Icons.dataset_rounded,
            ),
            EmbeddedHeaderBadge(
              label: '归档',
              value: saveToStorage ? '资产模式' : '会话模式',
              accent: saveToStorage ? AppColors.primary : AppColors.warning,
              icon: saveToStorage
                  ? Icons.cloud_done_rounded
                  : Icons.timer_outlined,
            ),
            EmbeddedHeaderBadge(
              label: '资产路径',
              value: latestStoragePath == null ? '未生成' : '已生成',
              accent: latestStoragePath == null
                  ? AppColors.textSecondary
                  : AppColors.cta,
              icon: latestStoragePath == null
                  ? Icons.route_outlined
                  : Icons.alt_route_rounded,
            ),
          ],
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.maxWidth;
            final crossAxisCount = width >= 1100
                ? 4
                : width >= 640
                ? 2
                : 1;
            final aspectRatio = crossAxisCount == 4 ? 1.7 : 1.9;

            return GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: crossAxisCount,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: aspectRatio,
              children: [
                MetricCard(
                  label: '数据行数',
                  value: result == null ? '--' : '${result.basicInfo.rows}',
                  icon: Icons.table_rows_rounded,
                  supportingText: pickedFile == null
                      ? '等待选择 CSV 文件'
                      : '当前数据集: ${pickedFile!.name}',
                ),
                MetricCard(
                  label: '字段数量',
                  value: result == null ? '--' : '${result.basicInfo.columns}',
                  icon: Icons.view_column_rounded,
                  supportingText: result == null
                      ? '分析完成后显示 schema 宽度'
                      : '字段结构已完成识别',
                ),
                MetricCard(
                  label: '质量评分',
                  value: qualityScore == null
                      ? '--'
                      : '${qualityScore.toStringAsFixed(0)} / 100',
                  icon: Icons.health_and_safety_rounded,
                  emphasis: qualityScore != null && qualityScore < 80,
                  supportingText: qualityScore == null
                      ? '等待质量检查输出'
                      : '综合缺失、重复与异常指标',
                ),
                MetricCard(
                  label: '高风险列',
                  value: result == null ? '--' : '$highRiskCount',
                  icon: Icons.warning_amber_rounded,
                  emphasis: highRiskCount > 0,
                  supportingText: result == null
                      ? '分析完成后显示治理优先级'
                      : highRiskCount == 0
                      ? '当前未发现高风险列'
                      : '建议优先治理这些字段',
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class DataAnalysisCommandDeck extends StatelessWidget {
  const DataAnalysisCommandDeck({
    super.key,
    required this.isAuthenticated,
    required this.hasFile,
    required this.isLoading,
    required this.isSubmittingBackgroundAnalysis,
    required this.saveToStorage,
    required this.analysisResult,
    required this.onStartAnalysis,
    required this.onSubmitBackgroundAnalysis,
    required this.onOpenHistory,
  });

  final bool isAuthenticated;
  final bool hasFile;
  final bool isLoading;
  final bool isSubmittingBackgroundAnalysis;
  final bool saveToStorage;
  final AnalysisResult? analysisResult;
  final VoidCallback onStartAnalysis;
  final VoidCallback onSubmitBackgroundAnalysis;
  final VoidCallback onOpenHistory;

  @override
  Widget build(BuildContext context) {
    final canAnalyze = isAuthenticated && hasFile && !isLoading;
    final hasResult = analysisResult != null;

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('工作流指挥台', style: AppTextStyles.h4),
          const SizedBox(height: 6),
          Text(
            '将数据分析拆成清晰的阶段控制。先完成身份和文件准备，再触发云端分析，最后决定是否进入 AI Lab。',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 16),
          _PipelineStageTile(
            index: 1,
            title: '身份验证',
            description: isAuthenticated ? '可访问私有数据与历史资产。' : '先登录后才能发起云端分析。',
            state: isAuthenticated
                ? _PipelineState.done
                : _PipelineState.blocked,
          ),
          _PipelineStageTile(
            index: 2,
            title: '数据集准备',
            description: hasFile ? 'CSV 已就绪，可直接送往分析引擎。' : '请选择单个 CSV 文件。',
            state: hasFile ? _PipelineState.done : _PipelineState.active,
          ),
          _PipelineStageTile(
            index: 3,
            title: '归档策略',
            description: saveToStorage ? '分析后将写入资产与历史。' : '本次结果只保留在当前会话。',
            state: saveToStorage
                ? _PipelineState.done
                : _PipelineState.optional,
          ),
          _PipelineStageTile(
            index: 4,
            title: '运行分析',
            description: hasResult ? '结果已生成，可继续查看质量、相关性和统计检验。' : '触发一次完整分析任务。',
            state: hasResult
                ? _PipelineState.done
                : canAnalyze
                ? _PipelineState.active
                : _PipelineState.blocked,
          ),
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: hasResult
                  ? AppColors.successLight
                  : AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
              border: Border.all(
                color: hasResult
                    ? AppColors.success.withValues(alpha: 0.18)
                    : AppColors.border,
              ),
            ),
            child: Text(
              _nextActionText(
                isAuthenticated: isAuthenticated,
                hasFile: hasFile,
                hasResult: hasResult,
                saveToStorage: saveToStorage,
              ),
              style: AppTextStyles.bodySmall.copyWith(
                color: hasResult ? AppColors.success : AppColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(height: 16),
          DataAnalysisStartButton(
            canAnalyze: canAnalyze,
            onStart: onStartAnalysis,
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.tonalIcon(
              onPressed: (canAnalyze && !isSubmittingBackgroundAnalysis)
                  ? onSubmitBackgroundAnalysis
                  : null,
              icon: isSubmittingBackgroundAnalysis
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.schedule_send_rounded),
              label: Text(
                isSubmittingBackgroundAnalysis ? '提交后台任务中...' : '提交后台分析任务',
              ),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onOpenHistory,
              icon: const Icon(Icons.history_rounded),
              label: const Text('查看历史与审计'),
            ),
          ),
        ],
      ),
    );
  }

  String _nextActionText({
    required bool isAuthenticated,
    required bool hasFile,
    required bool hasResult,
    required bool saveToStorage,
  }) {
    if (!isAuthenticated) {
      return '下一步: 建立用户会话。登录后才能访问上传、历史与云端分析能力。';
    }
    if (!hasFile) {
      return '下一步: 选择一个 CSV 文件作为当前工作数据集。';
    }
    if (!hasResult) {
      return '下一步: 触发分析任务，生成质量、相关性和统计结论。';
    }
    if (!saveToStorage) {
      return '当前结果只存在于本次会话中。如需进入 AI Lab 或沉淀历史，请下次开启归档。';
    }
    return '当前数据资产已可进入后续工作流，可继续查看详细面板或送入 AI Lab。';
  }
}

class DataAnalysisWorkflowActionsCard extends StatelessWidget {
  const DataAnalysisWorkflowActionsCard({
    super.key,
    this.chain,
    required this.storagePath,
    required this.savedAsAsset,
    required this.schemaDigest,
    required this.governanceDigest,
    required this.assetPassport,
    required this.compareDigest,
    required this.collaborationBrief,
    required this.onOpenHistory,
    required this.onCopyStoragePath,
    required this.onCopySchemaDigest,
    required this.onCopyGovernanceDigest,
    required this.onCopyAssetPassport,
    required this.onCopyCompareDigest,
    required this.onCopyCollaborationBrief,
    this.onSendToTraining,
    this.onSendToRag,
  });

  final AssetChainSummary? chain;
  final String? storagePath;
  final bool savedAsAsset;
  final String schemaDigest;
  final String governanceDigest;
  final String assetPassport;
  final String compareDigest;
  final String collaborationBrief;
  final VoidCallback onOpenHistory;
  final VoidCallback onCopyStoragePath;
  final VoidCallback onCopySchemaDigest;
  final VoidCallback onCopyGovernanceDigest;
  final VoidCallback onCopyAssetPassport;
  final VoidCallback onCopyCompareDigest;
  final VoidCallback onCopyCollaborationBrief;
  final VoidCallback? onSendToTraining;
  final VoidCallback? onSendToRag;

  @override
  Widget build(BuildContext context) {
    final hasStoragePath = storagePath != null && storagePath!.isNotEmpty;

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('分析后续动作', style: AppTextStyles.h4),
              const Spacer(),
              _StatusChip(
                label: savedAsAsset ? '已写入资产链路' : '未归档，仅当前会话',
                icon: savedAsAsset
                    ? Icons.cloud_done_rounded
                    : Icons.warning_amber_rounded,
                foreground: savedAsAsset
                    ? AppColors.success
                    : AppColors.warning,
                background: savedAsAsset
                    ? AppColors.successLight
                    : AppColors.warningLight,
              ),
            ],
          ),
          if (chain != null) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _StatusChip(
                  label: chain!.workspaceTargetLabel,
                  icon: Icons.account_tree_rounded,
                  foreground: AppColors.primary,
                  background: AppColors.infoLight,
                ),
                _StatusChip(
                  label: chain!.incidentTargetLabel,
                  icon: Icons.adjust_rounded,
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
              ],
            ),
            const SizedBox(height: 12),
            _WorkflowContextBanner(
              accent: AppColors.primary,
              sectionLabel: chain!.workspaceTargetLabel,
              focusLabel: chain!.sectionTargetLabel,
              incidentLabel: chain!.incidentTargetLabel,
              incidentSummary: chain!.workspaceBrief,
            ),
          ],
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Storage Path', style: AppTextStyles.labelMedium),
                const SizedBox(height: 8),
                SelectableText(
                  hasStoragePath ? storagePath! : '当前分析未生成可复用的存储路径',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: hasStoragePath
                        ? AppColors.textPrimary
                        : AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final stacked = constraints.maxWidth < 920;
              final cards = [
                _WorkflowDigestCard(
                  title: 'Schema Digest',
                  value: schemaDigest,
                  icon: Icons.schema_rounded,
                  accent: AppColors.primary,
                  onCopy: onCopySchemaDigest,
                ),
                _WorkflowDigestCard(
                  title: '治理摘要',
                  value: governanceDigest,
                  icon: Icons.health_and_safety_rounded,
                  accent: AppColors.cta,
                  onCopy: onCopyGovernanceDigest,
                ),
                _WorkflowDigestCard(
                  title: 'Asset Passport',
                  value: assetPassport,
                  icon: Icons.badge_rounded,
                  accent: AppColors.success,
                  onCopy: onCopyAssetPassport,
                ),
                _WorkflowDigestCard(
                  title: 'Compare Digest',
                  value: compareDigest,
                  icon: Icons.compare_arrows_rounded,
                  accent: AppColors.warning,
                  onCopy: onCopyCompareDigest,
                ),
                _WorkflowDigestCard(
                  title: '协作摘要',
                  value: collaborationBrief,
                  icon: Icons.group_work_rounded,
                  accent: AppColors.primary,
                  onCopy: onCopyCollaborationBrief,
                ),
              ];

              if (stacked) {
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
                        width: (constraints.maxWidth - 24) / 2,
                        child: card,
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
          const SizedBox(height: 16),
          _WorkflowHandoffBoard(
            chain: chain,
            hasStoragePath: hasStoragePath,
            savedAsAsset: savedAsAsset,
            onOpenHistory: onOpenHistory,
            onCopyGovernanceDigest: onCopyGovernanceDigest,
            onCopyAssetPassport: onCopyAssetPassport,
            onCopyCompareDigest: onCopyCompareDigest,
            onCopyCollaborationBrief: onCopyCollaborationBrief,
            onSendToTraining: onSendToTraining,
            onSendToRag: onSendToRag,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              FilledButton.tonalIcon(
                onPressed: onOpenHistory,
                icon: const Icon(Icons.history_rounded),
                label: const Text('查看历史与审计'),
              ),
              OutlinedButton.icon(
                onPressed: hasStoragePath ? onCopyStoragePath : null,
                icon: const Icon(Icons.content_copy_rounded),
                label: const Text('复制 Storage Path'),
              ),
              FilledButton.icon(
                onPressed: hasStoragePath ? onSendToTraining : null,
                icon: const Icon(Icons.model_training_rounded),
                label: const Text('送入训练'),
              ),
              FilledButton.tonalIcon(
                onPressed: hasStoragePath ? onSendToRag : null,
                icon: const Icon(Icons.auto_awesome_rounded),
                label: const Text('送入 RAG'),
              ),
              OutlinedButton.icon(
                onPressed: onCopyAssetPassport,
                icon: const Icon(Icons.badge_rounded),
                label: const Text('复制资产护照'),
              ),
              OutlinedButton.icon(
                onPressed: onCopyCollaborationBrief,
                icon: const Icon(Icons.share_rounded),
                label: const Text('复制协作摘要'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            hasStoragePath
                ? '建议先查看质量与相关性面板，再决定是否进入训练或知识库流程。'
                : '当前结果尚未落地为可复用资产，因此无法直接进入 AI Lab。',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _WorkflowHandoffBoard extends StatelessWidget {
  const _WorkflowHandoffBoard({
    this.chain,
    required this.hasStoragePath,
    required this.savedAsAsset,
    required this.onOpenHistory,
    required this.onCopyGovernanceDigest,
    required this.onCopyAssetPassport,
    required this.onCopyCompareDigest,
    required this.onCopyCollaborationBrief,
    this.onSendToTraining,
    this.onSendToRag,
  });

  final AssetChainSummary? chain;
  final bool hasStoragePath;
  final bool savedAsAsset;
  final VoidCallback onOpenHistory;
  final VoidCallback onCopyGovernanceDigest;
  final VoidCallback onCopyAssetPassport;
  final VoidCallback onCopyCompareDigest;
  final VoidCallback onCopyCollaborationBrief;
  final VoidCallback? onSendToTraining;
  final VoidCallback? onSendToRag;

  @override
  Widget build(BuildContext context) {
    final lanes = [
      _HandoffLane(
        title: '训练交接',
        description: hasStoragePath
            ? '将资产护照和对比摘要一并送入训练工作台，保留资产来源和基线差异。'
            : '缺少可复用 Storage Path，当前无法直接进入训练链路。',
        accent: AppColors.cta,
        icon: Icons.model_training_rounded,
        contextLabel: chain?.workspaceTargetLabel,
        incidentLabel: chain?.incidentTargetLabel,
        incidentSummary: chain?.workspaceBrief,
        statusLabel: hasStoragePath ? 'Ready' : 'Blocked',
        statusColor: hasStoragePath ? AppColors.success : AppColors.warning,
        actions: [
          _HandoffLaneAction(
            label: '送入训练',
            icon: Icons.arrow_forward_rounded,
            onTap: hasStoragePath ? onSendToTraining : null,
            filled: true,
          ),
          _HandoffLaneAction(
            label: '复制资产护照',
            icon: Icons.badge_rounded,
            onTap: onCopyAssetPassport,
          ),
          _HandoffLaneAction(
            label: '复制对比摘要',
            icon: Icons.compare_arrows_rounded,
            onTap: onCopyCompareDigest,
          ),
        ],
      ),
      _HandoffLane(
        title: '知识库交接',
        description: hasStoragePath
            ? '将资产路径和协作摘要带入 RAG 构建入口，避免知识库来源脱节。'
            : '当前分析结果尚未沉淀为资产，不能直接进入知识库构建流程。',
        accent: AppColors.primary,
        icon: Icons.auto_awesome_rounded,
        contextLabel: chain?.workspaceTargetLabel,
        incidentLabel: chain?.incidentTargetLabel,
        incidentSummary: chain?.workspaceBrief,
        statusLabel: hasStoragePath ? 'Ready' : 'Blocked',
        statusColor: hasStoragePath ? AppColors.success : AppColors.warning,
        actions: [
          _HandoffLaneAction(
            label: '送入 RAG',
            icon: Icons.hub_rounded,
            onTap: hasStoragePath ? onSendToRag : null,
            filled: true,
          ),
          _HandoffLaneAction(
            label: '复制资产护照',
            icon: Icons.badge_rounded,
            onTap: onCopyAssetPassport,
          ),
          _HandoffLaneAction(
            label: '复制协作摘要',
            icon: Icons.share_rounded,
            onTap: onCopyCollaborationBrief,
          ),
        ],
      ),
      _HandoffLane(
        title: '协作与审计',
        description: savedAsAsset
            ? '资产已经进入历史链路，可直接把治理摘要和协作摘要交给审计或团队协作。'
            : '即使未归档，也可以先复制治理摘要供人工审核，但不会进入资产台账。',
        accent: AppColors.success,
        icon: Icons.fact_check_rounded,
        contextLabel: savedAsAsset ? '资产已登记' : chain?.workspaceTargetLabel,
        incidentLabel: chain?.incidentTargetLabel,
        incidentSummary: chain?.workspaceBrief,
        statusLabel: savedAsAsset ? 'Tracked' : 'Session Only',
        statusColor: savedAsAsset ? AppColors.success : AppColors.warning,
        actions: [
          _HandoffLaneAction(
            label: '打开历史与审计',
            icon: Icons.history_rounded,
            onTap: onOpenHistory,
            filled: true,
          ),
          _HandoffLaneAction(
            label: '复制治理摘要',
            icon: Icons.health_and_safety_rounded,
            onTap: onCopyGovernanceDigest,
          ),
          _HandoffLaneAction(
            label: '复制协作摘要',
            icon: Icons.groups_rounded,
            onTap: onCopyCollaborationBrief,
          ),
        ],
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final stacked = constraints.maxWidth < 980;
        if (stacked) {
          return Column(
            children: [
              for (var i = 0; i < lanes.length; i++) ...[
                lanes[i],
                if (i < lanes.length - 1) const SizedBox(height: 12),
              ],
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (var i = 0; i < lanes.length; i++) ...[
              Expanded(child: lanes[i]),
              if (i < lanes.length - 1) const SizedBox(width: 12),
            ],
          ],
        );
      },
    );
  }
}

class _HandoffLane extends StatelessWidget {
  const _HandoffLane({
    required this.title,
    required this.description,
    required this.accent,
    required this.icon,
    this.contextLabel,
    this.incidentLabel,
    this.incidentSummary,
    required this.statusLabel,
    required this.statusColor,
    required this.actions,
  });

  final String title;
  final String description;
  final Color accent;
  final IconData icon;
  final String? contextLabel;
  final String? incidentLabel;
  final String? incidentSummary;
  final String statusLabel;
  final Color statusColor;
  final List<_HandoffLaneAction> actions;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: accent.withValues(alpha: 0.14)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: Icon(icon, size: 18, color: accent),
              ),
              const SizedBox(width: 10),
              Expanded(child: Text(title, style: AppTextStyles.labelLarge)),
              if (contextLabel != null && contextLabel!.isNotEmpty) ...[
                _StatusChip(
                  label: contextLabel!,
                  icon: Icons.account_tree_rounded,
                  foreground: accent,
                  background: accent.withValues(alpha: 0.12),
                ),
                const SizedBox(width: 8),
              ],
              _StatusChip(
                label: statusLabel,
                icon: Icons.radio_button_checked_rounded,
                foreground: statusColor,
                background: statusColor.withValues(alpha: 0.12),
              ),
            ],
          ),
          if ((incidentLabel ?? '').isNotEmpty ||
              (incidentSummary ?? '').isNotEmpty) ...[
            const SizedBox(height: 12),
            _WorkflowContextBanner(
              accent: accent,
              sectionLabel: contextLabel,
              focusLabel: statusLabel,
              incidentLabel: incidentLabel,
              incidentSummary: incidentSummary,
            ),
          ],
          const SizedBox(height: 10),
          Text(
            description,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: actions
                .map(
                  (action) => action.filled
                      ? FilledButton.tonalIcon(
                          onPressed: action.onTap,
                          icon: Icon(action.icon),
                          label: Text(action.label),
                        )
                      : OutlinedButton.icon(
                          onPressed: action.onTap,
                          icon: Icon(action.icon),
                          label: Text(action.label),
                        ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class _HandoffLaneAction {
  const _HandoffLaneAction({
    required this.label,
    required this.icon,
    required this.onTap,
    this.filled = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final bool filled;
}

class _WorkflowContextBanner extends StatelessWidget {
  const _WorkflowContextBanner({
    required this.accent,
    this.sectionLabel,
    this.focusLabel,
    this.incidentLabel,
    this.incidentSummary,
  });

  final Color accent;
  final String? sectionLabel;
  final String? focusLabel;
  final String? incidentLabel;
  final String? incidentSummary;

  @override
  Widget build(BuildContext context) {
    final hasSignal =
        (sectionLabel ?? '').isNotEmpty ||
        (focusLabel ?? '').isNotEmpty ||
        (incidentLabel ?? '').isNotEmpty ||
        (incidentSummary ?? '').isNotEmpty;
    if (!hasSignal) {
      return const SizedBox.shrink();
    }

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
              if ((sectionLabel ?? '').isNotEmpty)
                _StatusChip(
                  label: sectionLabel!,
                  icon: Icons.account_tree_rounded,
                  foreground: accent,
                  background: accent.withValues(alpha: 0.12),
                ),
              if ((focusLabel ?? '').isNotEmpty)
                _StatusChip(
                  label: focusLabel!,
                  icon: Icons.adjust_rounded,
                  foreground: AppColors.textPrimary,
                  background: AppColors.surfaceVariant,
                ),
              if ((incidentLabel ?? '').isNotEmpty)
                _StatusChip(
                  label: 'Current watch · $incidentLabel',
                  icon: Icons.priority_high_rounded,
                  foreground: accent,
                  background: accent.withValues(alpha: 0.12),
                ),
            ],
          ),
          if ((incidentSummary ?? '').isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              incidentSummary!,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _WorkflowDigestCard extends StatelessWidget {
  const _WorkflowDigestCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.accent,
    required this.onCopy,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color accent;
  final VoidCallback onCopy;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: accent),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: AppTextStyles.labelLarge)),
              IconButton(
                onPressed: onCopy,
                tooltip: '复制$title',
                icon: const Icon(Icons.content_copy_rounded, size: 18),
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.icon,
    required this.foreground,
    required this.background,
  });

  final String label;
  final IconData icon;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: foreground),
          const SizedBox(width: 8),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 220),
            child: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: AppTextStyles.labelMedium.copyWith(
                color: foreground,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

enum _PipelineState { done, active, optional, blocked }

class _PipelineStageTile extends StatelessWidget {
  const _PipelineStageTile({
    required this.index,
    required this.title,
    required this.description,
    required this.state,
  });

  final int index;
  final String title;
  final String description;
  final _PipelineState state;

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(state);

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: tone.background,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: state == _PipelineState.done
                ? Icon(Icons.check_rounded, size: 18, color: tone.foreground)
                : Text(
                    '$index',
                    style: AppTextStyles.labelMedium.copyWith(
                      color: tone.foreground,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: AppTextStyles.labelLarge),
                const SizedBox(height: 2),
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
    );
  }

  ({Color background, Color foreground}) _toneFor(_PipelineState value) {
    switch (value) {
      case _PipelineState.done:
        return (
          background: AppColors.successLight,
          foreground: AppColors.success,
        );
      case _PipelineState.active:
        return (background: AppColors.infoLight, foreground: AppColors.primary);
      case _PipelineState.optional:
        return (
          background: AppColors.warningLight,
          foreground: AppColors.warning,
        );
      case _PipelineState.blocked:
        return (
          background: AppColors.surfaceVariant,
          foreground: AppColors.textSecondary,
        );
    }
  }
}
