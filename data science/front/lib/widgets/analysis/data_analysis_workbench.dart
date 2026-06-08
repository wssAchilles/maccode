/// 数据分析工作台组件
library;

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/analysis_result.dart';
import '../../models/dashboard_summary.dart';
import '../../models/workbench_launch_context.dart';
import '../common/glass_card.dart';
import '../operations/embedded_page_header.dart';
import '../operations/metric_card.dart';
import '../operations/workspace_action_lane.dart';
import '../operations/workspace_digest_card.dart';
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
    final nextActionText = _nextActionText(
      isAuthenticated: isAuthenticated,
      hasFile: hasFile,
      hasResult: hasResult,
      saveToStorage: saveToStorage,
    );

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
              nextActionText,
              style: AppTextStyles.bodySmall.copyWith(
                color: hasResult ? AppColors.success : AppColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(height: 16),
          DataAnalysisStartButton(
            canAnalyze: canAnalyze,
            onStart: onStartAnalysis,
            disabledReason: canAnalyze ? null : nextActionText,
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
    this.continuationContext,
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
  final WorkbenchLaunchContext? continuationContext;
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
    final workspaceLabel =
        continuationContext?.workspaceTargetLabel ??
        chain?.workspaceTargetLabel;
    final cardLabel =
        continuationContext?.cardTargetLabel ?? chain?.cardTargetLabel;
    final incidentLabel =
        continuationContext?.incidentTargetLabel ?? chain?.incidentTargetLabel;
    final workspaceBrief =
        continuationContext?.workspaceBrief ?? chain?.workspaceBrief;

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('分析后续动作', style: AppTextStyles.h4),
              const Spacer(),
              WorkspaceStatusChip(
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
            WorkspaceContextBanner(
              accent: AppColors.primary,
              workspaceLabel: workspaceLabel,
              cardLabel: cardLabel,
              incidentLabel: incidentLabel,
              summary: workspaceBrief,
            ),
          ],
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Icon(
                  hasStoragePath
                      ? Icons.folder_rounded
                      : Icons.folder_off_rounded,
                  size: 18,
                  color: hasStoragePath
                      ? AppColors.primary
                      : AppColors.textSecondary,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    hasStoragePath ? storagePath! : '当前分析未生成可复用的存储路径',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: hasStoragePath
                          ? AppColors.textPrimary
                          : AppColors.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          WorkspaceDigestList(
            items: [
              WorkspaceDigestListItem(
                title: 'Schema Digest',
                value: schemaDigest,
                icon: Icons.schema_rounded,
                accent: AppColors.primary,
                onCopy: onCopySchemaDigest,
              ),
              WorkspaceDigestListItem(
                title: '治理摘要',
                value: governanceDigest,
                icon: Icons.health_and_safety_rounded,
                accent: AppColors.cta,
                onCopy: onCopyGovernanceDigest,
              ),
              WorkspaceDigestListItem(
                title: 'Asset Passport',
                value: assetPassport,
                icon: Icons.badge_rounded,
                accent: AppColors.success,
                onCopy: onCopyAssetPassport,
              ),
              WorkspaceDigestListItem(
                title: 'Compare Digest',
                value: compareDigest,
                icon: Icons.compare_arrows_rounded,
                accent: AppColors.warning,
                onCopy: onCopyCompareDigest,
              ),
              WorkspaceDigestListItem(
                title: '协作摘要',
                value: collaborationBrief,
                icon: Icons.group_work_rounded,
                accent: AppColors.primary,
                onCopy: onCopyCollaborationBrief,
              ),
            ],
          ),
          const SizedBox(height: 16),
          _WorkflowHandoffBoard(
            chain: chain,
            continuationContext: continuationContext,
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
          WorkspaceInlineActionBar(
            spacing: 12,
            runSpacing: 12,
            recommendedActionKey: _recommendedWorkflowActionKey(
              continuationContext,
              hasStoragePath: hasStoragePath,
            ),
            actions: [
              WorkspaceActionLaneAction(
                label: '查看历史与审计',
                icon: Icons.history_rounded,
                onTap: onOpenHistory,
                semanticKey: 'open_history',
                tone: WorkspaceActionLaneTone.tonal,
              ),
              WorkspaceActionLaneAction(
                label: '复制 Storage Path',
                icon: Icons.content_copy_rounded,
                onTap: hasStoragePath ? onCopyStoragePath : null,
                semanticKey: 'copy_storage_path',
              ),
              WorkspaceActionLaneAction(
                label: '送入训练',
                icon: Icons.model_training_rounded,
                onTap: hasStoragePath ? onSendToTraining : null,
                semanticKey: 'send_training',
                tone: WorkspaceActionLaneTone.primary,
              ),
              WorkspaceActionLaneAction(
                label: '送入 RAG',
                icon: Icons.auto_awesome_rounded,
                onTap: hasStoragePath ? onSendToRag : null,
                semanticKey: 'send_rag',
                tone: WorkspaceActionLaneTone.tonal,
              ),
              WorkspaceActionLaneAction(
                label: '复制资产护照',
                icon: Icons.badge_rounded,
                onTap: onCopyAssetPassport,
                semanticKey: 'copy_asset_passport',
              ),
              WorkspaceActionLaneAction(
                label: '复制协作摘要',
                icon: Icons.share_rounded,
                onTap: onCopyCollaborationBrief,
                semanticKey: 'copy_collaboration_brief',
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
    this.continuationContext,
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
  final WorkbenchLaunchContext? continuationContext;
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
    final workspaceLabel =
        continuationContext?.workspaceTargetLabel ??
        chain?.workspaceTargetLabel;
    final cardLabel =
        continuationContext?.cardTargetLabel ?? chain?.cardTargetLabel;
    final incidentLabel =
        continuationContext?.incidentTargetLabel ?? chain?.incidentTargetLabel;
    final workspaceBrief =
        continuationContext?.workspaceBrief ?? chain?.workspaceBrief;
    final lanes = [
      WorkspaceActionLane(
        title: '训练交接',
        description: hasStoragePath
            ? '将资产护照和对比摘要一并送入训练工作台，保留资产来源和基线差异。'
            : '缺少可复用 Storage Path，当前无法直接进入训练链路。',
        accent: AppColors.cta,
        icon: Icons.model_training_rounded,
        workspaceLabel: workspaceLabel,
        cardLabel: cardLabel,
        incidentLabel: incidentLabel,
        summary: workspaceBrief,
        statusLabel: hasStoragePath ? '就绪' : '待完成',
        statusColor: hasStoragePath ? AppColors.success : AppColors.warning,
        recommendedActionKey: hasStoragePath
            ? 'send_training'
            : 'copy_asset_passport',
        actions: [
          WorkspaceActionLaneAction(
            label: '送入训练',
            icon: Icons.arrow_forward_rounded,
            onTap: hasStoragePath ? onSendToTraining : null,
            semanticKey: 'send_training',
            tone: WorkspaceActionLaneTone.primary,
          ),
          WorkspaceActionLaneAction(
            label: '复制资产护照',
            icon: Icons.badge_rounded,
            onTap: onCopyAssetPassport,
            semanticKey: 'copy_asset_passport',
          ),
          WorkspaceActionLaneAction(
            label: '复制对比摘要',
            icon: Icons.compare_arrows_rounded,
            onTap: onCopyCompareDigest,
            semanticKey: 'copy_compare_digest',
          ),
        ],
      ),
      WorkspaceActionLane(
        title: '知识库交接',
        description: hasStoragePath
            ? '将资产路径和协作摘要带入 RAG 构建入口，避免知识库来源脱节。'
            : '当前分析结果尚未沉淀为资产，不能直接进入知识库构建流程。',
        accent: AppColors.primary,
        icon: Icons.auto_awesome_rounded,
        workspaceLabel: workspaceLabel,
        cardLabel: cardLabel,
        incidentLabel: incidentLabel,
        summary: workspaceBrief,
        statusLabel: hasStoragePath ? '就绪' : '待完成',
        statusColor: hasStoragePath ? AppColors.success : AppColors.warning,
        recommendedActionKey: hasStoragePath
            ? 'send_rag'
            : 'copy_asset_passport',
        actions: [
          WorkspaceActionLaneAction(
            label: '送入 RAG',
            icon: Icons.hub_rounded,
            onTap: hasStoragePath ? onSendToRag : null,
            semanticKey: 'send_rag',
            tone: WorkspaceActionLaneTone.primary,
          ),
          WorkspaceActionLaneAction(
            label: '复制资产护照',
            icon: Icons.badge_rounded,
            onTap: onCopyAssetPassport,
            semanticKey: 'copy_asset_passport',
          ),
          WorkspaceActionLaneAction(
            label: '复制协作摘要',
            icon: Icons.share_rounded,
            onTap: onCopyCollaborationBrief,
            semanticKey: 'copy_collaboration_brief',
          ),
        ],
      ),
      WorkspaceActionLane(
        title: '协作与审计',
        description: savedAsAsset
            ? '资产已经进入历史链路，可直接把治理摘要和协作摘要交给审计或团队协作。'
            : '即使未归档，也可以先复制治理摘要供人工审核，但不会进入资产台账。',
        accent: AppColors.success,
        icon: Icons.fact_check_rounded,
        workspaceLabel: savedAsAsset
            ? (workspaceLabel ?? '资产已登记')
            : workspaceLabel,
        cardLabel: cardLabel,
        incidentLabel: incidentLabel,
        summary: workspaceBrief,
        statusLabel: savedAsAsset ? 'Tracked' : 'Session Only',
        statusColor: savedAsAsset ? AppColors.success : AppColors.warning,
        recommendedActionKey: savedAsAsset
            ? 'open_history'
            : 'copy_governance_digest',
        actions: [
          WorkspaceActionLaneAction(
            label: '打开历史与审计',
            icon: Icons.history_rounded,
            onTap: onOpenHistory,
            semanticKey: 'open_history',
            tone: WorkspaceActionLaneTone.primary,
          ),
          WorkspaceActionLaneAction(
            label: '复制治理摘要',
            icon: Icons.health_and_safety_rounded,
            onTap: onCopyGovernanceDigest,
            semanticKey: 'copy_governance_digest',
          ),
          WorkspaceActionLaneAction(
            label: '复制协作摘要',
            icon: Icons.groups_rounded,
            onTap: onCopyCollaborationBrief,
            semanticKey: 'copy_collaboration_brief',
          ),
        ],
      ),
    ];

    return WorkspaceActionDeck(lanes: lanes);
  }
}

String _recommendedWorkflowActionKey(
  WorkbenchLaunchContext? context, {
  required bool hasStoragePath,
}) {
  switch (context?.workspaceTarget) {
    case 'data_governance':
      switch (context?.cardTarget) {
        case 'schema_topology':
          return 'copy_storage_path';
        case 'field_distribution':
          return hasStoragePath ? 'send_rag' : 'copy_asset_passport';
        case 'risk_digest':
        case 'governance_decision':
          return 'copy_collaboration_brief';
        case 'current_asset':
        case 'reference_asset':
        case 'drift_report':
          return 'copy_asset_passport';
      }
      return 'copy_asset_passport';
    case 'data_handoff':
      return hasStoragePath ? 'send_training' : 'copy_collaboration_brief';
    case 'data_job_center':
      return 'open_history';
    default:
      return hasStoragePath ? 'send_training' : 'open_history';
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
