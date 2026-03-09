/// 数据分析工作台组件
library;

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/analysis_result.dart';
import '../common/glass_card.dart';
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
        GlassCard(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Data Analysis Workbench', style: AppTextStyles.h2),
              const SizedBox(height: 10),
              Text(
                '将认证、CSV 上传、质量审查、统计分析和 AI hand-off 收到同一工作台，减少页面跳转与上下文丢失。',
                style: AppTextStyles.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 18),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _StatusChip(
                    label: currentUser == null ? '未登录' : '会话已连接',
                    icon: currentUser == null
                        ? Icons.lock_outline_rounded
                        : Icons.verified_user_rounded,
                    foreground: currentUser == null
                        ? AppColors.warning
                        : AppColors.success,
                    background: currentUser == null
                        ? AppColors.warningLight
                        : AppColors.successLight,
                  ),
                  _StatusChip(
                    label: pickedFile == null ? '未选择数据集' : pickedFile!.name,
                    icon: pickedFile == null
                        ? Icons.upload_file_outlined
                        : Icons.dataset_rounded,
                    foreground: pickedFile == null
                        ? AppColors.textSecondary
                        : AppColors.primary,
                    background: pickedFile == null
                        ? AppColors.surfaceVariant
                        : AppColors.infoLight,
                  ),
                  _StatusChip(
                    label: saveToStorage ? '结果归档开启' : '仅本次会话结果',
                    icon: saveToStorage
                        ? Icons.cloud_done_rounded
                        : Icons.timer_outlined,
                    foreground: saveToStorage
                        ? AppColors.primary
                        : AppColors.warning,
                    background: saveToStorage
                        ? AppColors.infoLight
                        : AppColors.warningLight,
                  ),
                  _StatusChip(
                    label: latestStoragePath == null ? '尚未生成资产路径' : '已生成资产路径',
                    icon: latestStoragePath == null
                        ? Icons.route_outlined
                        : Icons.alt_route_rounded,
                    foreground: latestStoragePath == null
                        ? AppColors.textSecondary
                        : AppColors.cta,
                    background: latestStoragePath == null
                        ? AppColors.surfaceVariant
                        : const Color(0xFFFFEDD5),
                  ),
                ],
              ),
            ],
          ),
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
    required this.storagePath,
    required this.savedAsAsset,
    required this.onOpenHistory,
    required this.onCopyStoragePath,
    this.onSendToTraining,
    this.onSendToRag,
  });

  final String? storagePath;
  final bool savedAsAsset;
  final VoidCallback onOpenHistory;
  final VoidCallback onCopyStoragePath;
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
