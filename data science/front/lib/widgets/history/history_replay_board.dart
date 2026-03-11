/// 历史与审计回放板
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/ai_lab_launch_intent.dart';
import '../../models/data_analysis_launch_intent.dart';
import '../../models/history_record.dart';
import '../../models/job_record.dart';
import '../../models/optimization_launch_intent.dart';
import '../common/glass_card.dart';

class HistoryReplayBoard extends StatelessWidget {
  const HistoryReplayBoard({
    super.key,
    required this.jobs,
    required this.records,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
  });

  final List<JobRecord> jobs;
  final List<HistoryRecord> records;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;

  @override
  Widget build(BuildContext context) {
    final replayableJobs = jobs
        .where(_isReplayableJob)
        .take(6)
        .toList(growable: false);
    final replayableRecords = records
        .where(
          (record) =>
              record.summary != null ||
              (record.storageUrl?.isNotEmpty ?? false),
        )
        .take(4)
        .toList(growable: false);

    return LayoutBuilder(
      builder: (context, constraints) {
        final stacked = constraints.maxWidth < 1180;
        final children = [
          _ReplayPanel(
            title: '任务回放',
            description: '把成功任务直接送回对应工作台，快速复盘参数、结果和阶段轨迹。',
            icon: Icons.replay_circle_filled_rounded,
            accent: AppColors.primary,
            emptyMessage: '暂无可回放任务。成功完成分析、优化、训练或知识库构建后，这里会出现快速入口。',
            items: replayableJobs
                .map(
                  (job) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _ReplayJobTile(
                      job: job,
                      onOpenAiLab: onOpenAiLab,
                      onOpenDataAnalysis: onOpenDataAnalysis,
                      onOpenOptimization: onOpenOptimization,
                    ),
                  ),
                )
                .toList(growable: false),
          ),
          _ReplayPanel(
            title: '数据资产回放',
            description: '把历史分析资产重新送入数据工作台、训练链路或知识库治理入口。',
            icon: Icons.inventory_2_rounded,
            accent: AppColors.cta,
            emptyMessage: '暂无可回放的数据资产。保存分析资产后，这里会出现治理入口。',
            items: replayableRecords
                .map(
                  (record) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _ReplayRecordTile(
                      record: record,
                      onOpenAiLab: onOpenAiLab,
                      onOpenDataAnalysis: onOpenDataAnalysis,
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ];

        if (stacked) {
          return Column(
            children: [children[0], const SizedBox(height: 16), children[1]],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: children[0]),
            const SizedBox(width: 16),
            Expanded(child: children[1]),
          ],
        );
      },
    );
  }
}

class _ReplayPanel extends StatelessWidget {
  const _ReplayPanel({
    required this.title,
    required this.description,
    required this.icon,
    required this.accent,
    required this.emptyMessage,
    required this.items,
  });

  final String title;
  final String description;
  final IconData icon;
  final Color accent;
  final String emptyMessage;
  final List<Widget> items;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: Icon(icon, size: 20, color: accent),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppTextStyles.h4),
                    const SizedBox(height: 4),
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
          const SizedBox(height: 14),
          if (items.isEmpty)
            Text(emptyMessage, style: AppTextStyles.bodySmall)
          else
            ...items,
        ],
      ),
    );
  }
}

class _ReplayJobTile extends StatelessWidget {
  const _ReplayJobTile({
    required this.job,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
    this.onOpenOptimization,
  });

  final JobRecord job;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;
  final ValueChanged<OptimizationLaunchIntent>? onOpenOptimization;

  @override
  Widget build(BuildContext context) {
    final statusText = job.statusMessage ?? job.status;
    final summary = switch (job.type) {
      'analysis' =>
        _firstString([job.result['storage_path'], job.input['storage_path']]) ??
            '分析产物',
      'optimization' => _firstString([job.result['message']]) ?? '优化结果',
      'ml_train' =>
        _firstString([job.result['model_path'], job.input['storage_path']]) ??
            '训练产物',
      'rag_ingest' =>
        _firstString([
              job.result['collection'],
              job.input['collection_name'],
            ]) ??
            '知识库快照',
      _ => job.type,
    };

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(job.displayTitle, style: AppTextStyles.labelLarge),
                    const SizedBox(height: 4),
                    Text(
                      '$summary · $statusText',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Text(
                job.completedAt == null
                    ? '--'
                    : DateFormat(
                        'MM-dd HH:mm',
                      ).format(job.completedAt!.toLocal()),
                style: AppTextStyles.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: _actions()),
        ],
      ),
    );
  }

  List<Widget> _actions() {
    switch (job.type) {
      case 'analysis':
        if (onOpenDataAnalysis == null) {
          return const [];
        }
        final intent = DataAnalysisLaunchIntent.fromJob(job);
        if (!intent.canHydrate) {
          return const [];
        }
        return [
          FilledButton.tonalIcon(
            onPressed: () => onOpenDataAnalysis!(intent),
            icon: const Icon(Icons.analytics_rounded),
            label: const Text('打开分析工作台'),
          ),
        ];
      case 'optimization':
        if (onOpenOptimization == null) {
          return const [];
        }
        return [
          FilledButton.tonalIcon(
            onPressed: () =>
                onOpenOptimization!(OptimizationLaunchIntent.fromJob(job)),
            icon: const Icon(Icons.bolt_rounded),
            label: const Text('打开优化工作台'),
          ),
        ];
      case 'ml_train':
        if (onOpenAiLab == null) {
          return const [];
        }
        final intent = AiLabLaunchIntent.fromTrainingJob(job);
        if (intent.storagePath.isEmpty) {
          return const [];
        }
        return [
          FilledButton.tonalIcon(
            onPressed: () => onOpenAiLab!(intent),
            icon: const Icon(Icons.auto_awesome_rounded),
            label: const Text('回到训练入口'),
          ),
        ];
      case 'rag_ingest':
        if (onOpenAiLab == null) {
          return const [];
        }
        final intent = AiLabLaunchIntent.fromRagJob(job);
        if (intent.storagePath.isEmpty) {
          return const [];
        }
        return [
          FilledButton.tonalIcon(
            onPressed: () => onOpenAiLab!(intent),
            icon: const Icon(Icons.account_tree_rounded),
            label: const Text('回到知识库入口'),
          ),
        ];
      default:
        return const [];
    }
  }
}

class _ReplayRecordTile extends StatelessWidget {
  const _ReplayRecordTile({
    required this.record,
    this.onOpenAiLab,
    this.onOpenDataAnalysis,
  });

  final HistoryRecord record;
  final ValueChanged<AiLabLaunchIntent>? onOpenAiLab;
  final ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis;

  @override
  Widget build(BuildContext context) {
    final quality = record.qualityScore == null
        ? '未评分'
        : record.qualityScore!.toStringAsFixed(1);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(record.filename, style: AppTextStyles.labelLarge),
                    const SizedBox(height: 4),
                    Text(
                      '质量评分 $quality',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Text(
                record.createdAt == null
                    ? '--'
                    : DateFormat(
                        'MM-dd HH:mm',
                      ).format(record.createdAt!.toLocal()),
                style: AppTextStyles.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (onOpenDataAnalysis != null && record.summary != null)
                FilledButton.tonalIcon(
                  onPressed: () => onOpenDataAnalysis!(
                    DataAnalysisLaunchIntent.fromHistoryRecord(record),
                  ),
                  icon: const Icon(Icons.analytics_rounded),
                  label: const Text('回到分析工作台'),
                ),
              if (onOpenAiLab != null &&
                  (record.storageUrl?.isNotEmpty ?? false))
                OutlinedButton.icon(
                  onPressed: () => onOpenAiLab!(
                    AiLabLaunchIntent.fromHistoryRecordForTraining(record),
                  ),
                  icon: const Icon(Icons.model_training_rounded),
                  label: const Text('送入训练'),
                ),
              if (onOpenAiLab != null &&
                  (record.storageUrl?.isNotEmpty ?? false))
                OutlinedButton.icon(
                  onPressed: () => onOpenAiLab!(
                    AiLabLaunchIntent.fromHistoryRecordForRag(record),
                  ),
                  icon: const Icon(Icons.account_tree_rounded),
                  label: const Text('送入知识库'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

bool _isReplayableJob(JobRecord job) {
  if (job.status != 'succeeded') {
    return false;
  }
  switch (job.type) {
    case 'analysis':
      return job.result['analysis_result'] is Map;
    case 'optimization':
      return job.result.isNotEmpty;
    case 'ml_train':
      return (_firstString([
            job.input['storage_path'],
            job.result['storage_path'],
          ])?.isNotEmpty ??
          false);
    case 'rag_ingest':
      return (_firstString([
            job.result['storage_path'],
            job.input['storage_path'],
          ])?.isNotEmpty ??
          false);
    default:
      return false;
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
