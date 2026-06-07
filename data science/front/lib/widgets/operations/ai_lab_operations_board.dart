/// AI Lab 运营态概览板
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/ai_lab_launch_intent.dart';
import '../../models/dashboard_summary.dart';
import '../../models/job_record.dart';
import '../../utils/system_status_localizer.dart';
import '../common/glass_card.dart';
import 'metric_card.dart';

class AiLabOperationsBoard extends StatelessWidget {
  const AiLabOperationsBoard({
    super.key,
    required this.summary,
    required this.trainingJobs,
    required this.ragJobs,
    required this.currentTab,
    required this.trainingStoragePath,
    required this.ragStoragePath,
    this.launchIntent,
  });

  final DashboardSummary? summary;
  final List<JobRecord> trainingJobs;
  final List<JobRecord> ragJobs;
  final String currentTab;
  final String trainingStoragePath;
  final String ragStoragePath;
  final AiLabLaunchIntent? launchIntent;

  @override
  Widget build(BuildContext context) {
    final kpis = summary?.kpis;
    final modelStatus = _statusByKey(summary?.systemStatus, 'model');
    final ragStatus = _statusByKey(summary?.systemStatus, 'rag');
    final activeTrainingJobs = trainingJobs
        .where((job) => job.isRunning)
        .length;
    final activeRagJobs = ragJobs.where((job) => job.isRunning).length;
    final latestTrainingJob = _primaryJob(trainingJobs);
    final latestRagJob = _primaryJob(ragJobs);
    final aiAlerts = (summary?.alerts ?? const <DashboardAlert>[])
        .where(
          (alert) =>
              alert.title.contains('模型') ||
              alert.title.contains('知识') ||
              alert.message.contains('模型') ||
              alert.message.contains('RAG') ||
              alert.message.contains('知识库'),
        )
        .length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 1100;
            final metricCards = [
              MetricCard(
                label: '训练队列',
                value: '$activeTrainingJobs',
                icon: Icons.model_training_rounded,
                supportingText: latestTrainingJob == null
                    ? '当前没有训练任务在运行'
                    : _queueSummaryText(
                        latestTrainingJob,
                        completedLabel: '最近训练已完成',
                        runningLabel: '训练任务运行中',
                        queuedLabel: '训练任务已排队',
                        failedLabel: '最近训练失败',
                        cancelledLabel: '最近训练已取消',
                      ),
                emphasis: activeTrainingJobs > 0,
              ),
              MetricCard(
                label: '知识库队列',
                value: '$activeRagJobs',
                icon: Icons.auto_awesome_rounded,
                supportingText: latestRagJob == null
                    ? '当前没有 ingest 任务在运行'
                    : _queueSummaryText(
                        latestRagJob,
                        completedLabel: '最近知识库任务已完成',
                        runningLabel: '知识库任务运行中',
                        queuedLabel: '知识库任务已排队',
                        failedLabel: '最近知识库任务失败',
                        cancelledLabel: '最近知识库任务已取消',
                      ),
              ),
              MetricCard(
                label: '模型资产',
                value: '${kpis?.modelCount ?? 0}',
                icon: Icons.inventory_2_rounded,
                supportingText: '驾驶舱登记的可复用模型数',
              ),
              MetricCard(
                label: 'AI 提醒',
                value: '$aiAlerts',
                icon: aiAlerts > 0
                    ? Icons.warning_amber_rounded
                    : Icons.shield_outlined,
                supportingText: aiAlerts > 0
                    ? '建议优先处理模型或知识服务风险'
                    : '当前未发现 AI 路径高优先提醒',
                emphasis: aiAlerts > 0,
              ),
            ];

            if (compact) {
              return Column(
                children: [
                  for (var i = 0; i < metricCards.length; i++) ...[
                    metricCards[i],
                    if (i < metricCards.length - 1) const SizedBox(height: 12),
                  ],
                ],
              );
            }

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var i = 0; i < metricCards.length; i++) ...[
                  Expanded(child: metricCards[i]),
                  if (i < metricCards.length - 1) const SizedBox(width: 12),
                ],
              ],
            );
          },
        ),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 1180;
            final panels = [
              _AiLabContextCard(
                currentTab: currentTab,
                launchIntent: launchIntent,
                trainingStoragePath: trainingStoragePath,
                ragStoragePath: ragStoragePath,
                modelStatus: modelStatus,
                ragStatus: ragStatus,
              ),
              _AiJobLaneCard(
                title: '训练车道',
                subtitle: 'LSTM/GRU 等训练任务会先进入这里排队和重试。',
                emptyMessage: '当前没有训练任务。配置数据集路径后即可提交。',
                accent: AppColors.cta,
                icon: Icons.model_training_rounded,
                jobs: trainingJobs,
                completedLabel: '最近训练已完成',
                runningLabel: '训练任务运行中',
                queuedLabel: '训练任务已排队',
                failedLabel: '最近训练失败',
                cancelledLabel: '最近训练已取消',
              ),
              _AiJobLaneCard(
                title: '知识库车道',
                subtitle: '文档抓取、切片、向量化和集合重建都在这里观测。',
                emptyMessage: '当前没有知识库任务。提供文档目录后即可构建。',
                accent: AppColors.primary,
                icon: Icons.account_tree_rounded,
                jobs: ragJobs,
                completedLabel: '最近知识库任务已完成',
                runningLabel: '知识库任务运行中',
                queuedLabel: '知识库任务已排队',
                failedLabel: '最近知识库任务失败',
                cancelledLabel: '最近知识库任务已取消',
              ),
            ];

            if (compact) {
              return Column(
                children: [
                  for (var i = 0; i < panels.length; i++) ...[
                    panels[i],
                    if (i < panels.length - 1) const SizedBox(height: 12),
                  ],
                ],
              );
            }

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(flex: 11, child: panels[0]),
                const SizedBox(width: 12),
                Expanded(flex: 9, child: panels[1]),
                const SizedBox(width: 12),
                Expanded(flex: 9, child: panels[2]),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _AiLabContextCard extends StatelessWidget {
  const _AiLabContextCard({
    required this.currentTab,
    required this.trainingStoragePath,
    required this.ragStoragePath,
    required this.modelStatus,
    required this.ragStatus,
    this.launchIntent,
  });

  final String currentTab;
  final String trainingStoragePath;
  final String ragStoragePath;
  final SystemStatusItem? modelStatus;
  final SystemStatusItem? ragStatus;
  final AiLabLaunchIntent? launchIntent;

  @override
  Widget build(BuildContext context) {
    final routedTarget = launchIntent?.target == AiLabLaunchTarget.deepLearning
        ? '深度学习训练'
        : launchIntent?.target == AiLabLaunchTarget.rag
        ? '知识助手 RAG'
        : '手工调度';

    final routedPath = launchIntent?.storagePath;

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(
                  Icons.hub_rounded,
                  color: AppColors.primary,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('AI 调度上下文', style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '把数据分析接力、模型服务就绪度和当前编辑路径集中到同一张运营卡上。',
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
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _ContextPill(
                label: '当前工作台',
                value: currentTab == 'deepLearning' ? '深度学习' : '知识助手 RAG',
                accent: AppColors.primary,
              ),
              _ContextPill(
                label: '最近接力',
                value: routedTarget,
                accent: launchIntent == null
                    ? AppColors.textSecondary
                    : AppColors.cta,
              ),
              if (modelStatus != null)
                _ContextPill(
                  label: '训练服务',
                  value: localizeSystemStatusMessage(modelStatus!.message),
                  accent: _statusColor(modelStatus!.status),
                ),
              if (ragStatus != null)
                _ContextPill(
                  label: '知识服务',
                  value: localizeSystemStatusMessage(ragStatus!.message),
                  accent: _statusColor(ragStatus!.status),
                ),
            ],
          ),
          const SizedBox(height: 16),
          _ContextRow(
            label: '训练路径',
            value: trainingStoragePath.isEmpty ? '未设置' : trainingStoragePath,
          ),
          _ContextRow(
            label: '知识路径',
            value: ragStoragePath.isEmpty ? '未设置' : ragStoragePath,
          ),
          _ContextRow(
            label: '接力路径',
            value: routedPath == null || routedPath.isEmpty
                ? '暂无最近接力'
                : routedPath,
          ),
          const SizedBox(height: 10),
          Text(
            _contextRecommendation(currentTab, launchIntent),
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _AiJobLaneCard extends StatelessWidget {
  const _AiJobLaneCard({
    required this.title,
    required this.subtitle,
    required this.emptyMessage,
    required this.accent,
    required this.icon,
    required this.jobs,
    required this.completedLabel,
    required this.runningLabel,
    required this.queuedLabel,
    required this.failedLabel,
    required this.cancelledLabel,
  });

  final String title;
  final String subtitle;
  final String emptyMessage;
  final Color accent;
  final IconData icon;
  final List<JobRecord> jobs;
  final String completedLabel;
  final String runningLabel;
  final String queuedLabel;
  final String failedLabel;
  final String cancelledLabel;

  @override
  Widget build(BuildContext context) {
    final latestJob = _primaryJob(jobs);
    final runningJobs = jobs.where((job) => job.isRunning).length;
    final failedJobs = jobs.where((job) => job.status == 'failed').length;
    final completedJobs = jobs.where((job) => job.status == 'succeeded').length;

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: Icon(icon, color: accent, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
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
          Row(
            children: [
              Expanded(
                child: _LaneMetric(label: '运行中', value: '$runningJobs'),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _LaneMetric(label: '已完成', value: '$completedJobs'),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _LaneMetric(label: '失败', value: '$failedJobs'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (latestJob == null)
            _EmptyLaneState(message: emptyMessage)
          else
            _LaneJobSnapshot(
              job: latestJob,
              accent: accent,
              completedLabel: completedLabel,
              runningLabel: runningLabel,
              queuedLabel: queuedLabel,
              failedLabel: failedLabel,
              cancelledLabel: cancelledLabel,
            ),
        ],
      ),
    );
  }
}

class _LaneMetric extends StatelessWidget {
  const _LaneMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: AppTextStyles.labelMedium.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 6),
        Text(value, style: AppTextStyles.h4),
      ],
    );
  }
}

class _LaneJobSnapshot extends StatelessWidget {
  const _LaneJobSnapshot({
    required this.job,
    required this.accent,
    required this.completedLabel,
    required this.runningLabel,
    required this.queuedLabel,
    required this.failedLabel,
    required this.cancelledLabel,
  });

  final JobRecord job;
  final Color accent;
  final String completedLabel;
  final String runningLabel;
  final String queuedLabel;
  final String failedLabel;
  final String cancelledLabel;

  @override
  Widget build(BuildContext context) {
    final latestEvent = job.latestEvent;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _queueSummaryText(
              job,
              completedLabel: completedLabel,
              runningLabel: runningLabel,
              queuedLabel: queuedLabel,
              failedLabel: failedLabel,
              cancelledLabel: cancelledLabel,
            ),
            style: AppTextStyles.labelLarge.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _ContextPill(
                label: '状态',
                value: _statusLabel(job.status),
                accent: _statusColor(job.status),
              ),
              if (latestEvent != null)
                _ContextPill(
                  label: '阶段',
                  value: _phaseLabel(latestEvent.phase),
                  accent: accent,
                ),
              _ContextPill(
                label: '尝试',
                value: '${job.attemptCount}/${job.maxAttempts}',
                accent: job.retryable
                    ? AppColors.warning
                    : AppColors.textSecondary,
              ),
            ],
          ),
          const SizedBox(height: 12),
          LinearProgressIndicator(
            value: job.progress.clamp(0, 100) / 100,
            minHeight: 8,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            backgroundColor: AppColors.background,
            color: accent,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text('${job.progress}%', style: AppTextStyles.labelMedium),
              const Spacer(),
              Text(
                _formatTime(job.submittedAt),
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          if (job.error != null) ...[
            const SizedBox(height: 10),
            Text(
              job.error!.message,
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
            ),
          ],
        ],
      ),
    );
  }
}

class _EmptyLaneState extends StatelessWidget {
  const _EmptyLaneState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.inbox_outlined, color: AppColors.textSecondary),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ContextPill extends StatelessWidget {
  const _ContextPill({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Text.rich(
        TextSpan(
          children: [
            TextSpan(
              text: '$label · ',
              style: AppTextStyles.labelMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            TextSpan(
              text: value,
              style: AppTextStyles.labelMedium.copyWith(
                color: accent,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ContextRow extends StatelessWidget {
  const _ContextRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 76,
            child: Text(
              label,
              style: AppTextStyles.labelMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              value,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

JobRecord? _primaryJob(List<JobRecord> jobs) {
  if (jobs.isEmpty) {
    return null;
  }
  return jobs.first;
}

SystemStatusItem? _statusByKey(List<SystemStatusItem>? items, String key) {
  if (items == null) {
    return null;
  }
  for (final item in items) {
    if (item.key == key) {
      return item;
    }
  }
  return null;
}

Color _statusColor(String status) {
  switch (status) {
    case 'ok':
    case 'succeeded':
      return AppColors.success;
    case 'warning':
    case 'running':
      return AppColors.warning;
    case 'error':
    case 'failed':
      return AppColors.error;
    case 'queued':
      return AppColors.primary;
    default:
      return AppColors.textSecondary;
  }
}

String _statusLabel(String status) {
  switch (status) {
    case 'queued':
      return '排队';
    case 'running':
      return '运行中';
    case 'succeeded':
      return '已完成';
    case 'failed':
      return '失败';
    case 'cancelled':
      return '已取消';
    default:
      return status;
  }
}

String _phaseLabel(String phase) {
  switch (phase) {
    case 'dataset':
      return '数据加载';
    case 'model_init':
      return '模型初始化';
    case 'training':
      return '训练';
    case 'artifact_upload':
      return '产物上传';
    case 'fetch_documents':
      return '文档抓取';
    case 'reset_collection':
      return '重建集合';
    case 'parsing':
      return '切片';
    case 'embedding':
      return '向量化';
    case 'packaging':
      return '封装';
    default:
      return '处理中';
  }
}

String _contextRecommendation(
  String currentTab,
  AiLabLaunchIntent? launchIntent,
) {
  if (launchIntent?.target == AiLabLaunchTarget.deepLearning) {
    return '当前最近一次接力来自分析结果，优先检查训练路径、目标列和窗口大小，然后直接提交训练任务。';
  }
  if (launchIntent?.target == AiLabLaunchTarget.rag) {
    return '当前最近一次接力来自分析结果，优先确认知识目录和集合名，再触发 ingest 任务构建知识库。';
  }
  if (currentTab == 'deepLearning') {
    return '当前工作台停留在训练侧，建议先确认数据路径与目标列，再查看最近训练队列是否存在失败重试。';
  }
  return '当前工作台停留在知识助手侧，建议先确认集合与文档路径，再观察最近 ingest 队列是否存在阻塞。';
}

String _formatTime(DateTime? value) {
  if (value == null) {
    return '时间未知';
  }
  return DateFormat('MM-dd HH:mm').format(value.toLocal());
}

String _queueSummaryText(
  JobRecord job, {
  required String completedLabel,
  required String runningLabel,
  required String queuedLabel,
  required String failedLabel,
  required String cancelledLabel,
}) {
  final statusMessage = job.statusMessage?.trim();
  final latestEventMessage = job.latestEvent?.message.trim();

  bool isGenericStatusMessage(String? value) {
    if (value == null || value.isEmpty) {
      return true;
    }
    final normalized = value.toLowerCase();
    return normalized == job.status.toLowerCase() ||
        normalized == 'job completed';
  }

  if (!isGenericStatusMessage(statusMessage)) {
    return statusMessage!;
  }
  if (job.status == 'running' &&
      latestEventMessage != null &&
      latestEventMessage.isNotEmpty) {
    return latestEventMessage;
  }

  switch (job.status) {
    case 'queued':
      return queuedLabel;
    case 'running':
      return runningLabel;
    case 'succeeded':
      return completedLabel;
    case 'failed':
      return job.error?.message ?? failedLabel;
    case 'cancelled':
      return cancelledLabel;
    default:
      return _statusLabel(job.status);
  }
}
