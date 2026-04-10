/// 作业阶段时间线
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import '../../utils/job_presentation.dart';
import '../../utils/operation_compute_metrics.dart';
import '../common/glass_card.dart';

class JobEventTimeline extends StatelessWidget {
  const JobEventTimeline({
    super.key,
    required this.job,
    this.title = '任务阶段轨迹',
    this.emptyMessage = '等待任务事件写入。',
    this.maxVisibleEvents = 8,
    this.onOpenOperation,
    this.onRetry,
    this.onCancel,
    this.onApprove,
    this.onReject,
  });

  final JobRecord job;
  final String title;
  final String emptyMessage;
  final int maxVisibleEvents;
  final VoidCallback? onOpenOperation;
  final VoidCallback? onRetry;
  final VoidCallback? onCancel;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;

  @override
  Widget build(BuildContext context) {
    final tone = _timelineTone(job.status);
    final events = _visibleEvents(job.events);

    return GlassCard(
      padding: const EdgeInsets.all(20),
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
                    Text(title, style: AppTextStyles.h4),
                    const SizedBox(height: 4),
                    Text(
                      '${job.displayTitle} · ${job.jobId.substring(0, math.min(8, job.jobId.length))}',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '尝试 ${job.attemptCount}/${job.maxAttempts}'
                      '${job.retryable ? ' · 可重试' : ''}',
                      style: AppTextStyles.bodySmall.copyWith(
                        color: job.retryable
                            ? AppColors.warning
                            : AppColors.textMuted,
                      ),
                    ),
                    if (job.currentStep != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        '当前步骤 · ${_phaseLabel(job.currentStep!.phase)} · ${job.currentStep!.toolName}',
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: tone.$2,
                      borderRadius: BorderRadius.circular(
                        AppDecorations.radiusFull,
                      ),
                    ),
                    child: Text(
                      tone.$1,
                      style: AppTextStyles.labelMedium.copyWith(
                        color: tone.$3,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  if (onOpenOperation != null) ...[
                    const SizedBox(height: 10),
                    TextButton.icon(
                      onPressed: onOpenOperation,
                      icon: const Icon(Icons.travel_explore_rounded),
                      label: const Text('查看运行'),
                    ),
                  ],
                  if (job.retryable && onRetry != null) ...[
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: onRetry,
                      icon: const Icon(Icons.restart_alt_rounded),
                      label: const Text('重试任务'),
                    ),
                  ],
                  if (!job.isTerminal &&
                      !job.cancelRequested &&
                      onCancel != null &&
                      !job.isAwaitingApproval) ...[
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: onCancel,
                      icon: const Icon(Icons.stop_circle_outlined),
                      label: const Text('取消任务'),
                    ),
                  ],
                ],
              ),
            ],
          ),
          if (job.isAwaitingApproval &&
              (onApprove != null || onReject != null)) ...[
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                if (onApprove != null)
                  FilledButton.icon(
                    onPressed: onApprove,
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('批准执行'),
                  ),
                if (onReject != null)
                  OutlinedButton.icon(
                    onPressed: onReject,
                    icon: const Icon(Icons.cancel_outlined),
                    label: const Text('驳回任务'),
                  ),
              ],
            ),
          ],
          const SizedBox(height: 16),
          if (events.isEmpty)
            Text(
              buildJobPrimaryText(job, fallback: emptyMessage),
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            )
          else
            Column(
              children: [
                for (var index = 0; index < events.length; index++)
                  _EventRow(
                    job: job,
                    event: events[index],
                    isLast: index == events.length - 1,
                  ),
              ],
            ),
          if (job.error != null) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.errorLight,
                borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                border: Border.all(
                  color: AppColors.error.withValues(alpha: 0.18),
                ),
              ),
              child: Text(
                job.error!.message,
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
              ),
            ),
          ],
          if (job.artifacts.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: job.artifacts
                  .take(3)
                  .map((artifact) {
                    return Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceVariant,
                        borderRadius: BorderRadius.circular(
                          AppDecorations.radiusFull,
                        ),
                      ),
                      child: Text(
                        '${artifact.type} · ${artifact.name}',
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    );
                  })
                  .toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }

  List<JobEvent> _visibleEvents(List<JobEvent> events) {
    if (events.length <= maxVisibleEvents) {
      return events;
    }
    return events.sublist(events.length - maxVisibleEvents);
  }

  (String, Color, Color) _timelineTone(String status) {
    switch (status) {
      case 'queued':
        return ('已排队', AppColors.infoLight, AppColors.primary);
      case 'awaiting_approval':
        return ('待审批', const Color(0xFFFFF4E5), AppColors.warning);
      case 'dispatching':
        return ('调度中', AppColors.infoLight, AppColors.primary);
      case 'retrying':
      case 'running':
        return (
          status == 'retrying' ? '重试中' : '进行中',
          const Color(0xFFFFEDD5),
          AppColors.cta,
        );
      case 'succeeded':
        return ('已完成', AppColors.successLight, AppColors.success);
      case 'failed':
        return ('失败', AppColors.errorLight, AppColors.error);
      default:
        return ('已取消', AppColors.surfaceVariant, AppColors.textSecondary);
    }
  }
}

String _phaseLabel(String value) {
  switch (value) {
    case 'approval':
      return '审批';
    case 'fetch_external_data':
      return '数据抓取';
    case 'prepare_dataset':
      return '数据准备';
    case 'profile_dataset':
      return '数据剖析';
    case 'run_quality_checks':
      return '质量检查';
    case 'run_stat_tests':
      return '统计检验';
    case 'train_forecast_model':
      return '模型训练';
    case 'evaluate_model':
      return '模型评估';
    case 'optimize_schedule':
      return '优化调度';
    case 'generate_report':
      return '报告生成';
    case 'publish_artifacts':
      return '产物发布';
    case 'ingest_knowledge_base':
      return '知识入库';
    case 'compute_rollout_prepare':
      return '治理预检';
    case 'compute_rollout_apply':
      return '治理应用';
    case 'compute_benchmark_prepare':
      return '准备 benchmark';
    case 'compute_benchmark_run':
      return '执行 benchmark';
    case 'compute_benchmark_publish':
      return '发布 benchmark';
    case 'queued':
      return '排队';
    case 'started':
      return '启动';
    case 'dataset':
      return '数据加载';
    case 'basic_analysis':
      return '基础剖析';
    case 'model_metadata':
      return '模型元数据';
    case 'quality':
      return '质量检查';
    case 'correlation':
      return '相关性';
    case 'statistical':
      return '统计检验';
    case 'forecast':
      return '预测';
    case 'solver':
      return '求解';
    case 'aggregation':
      return '汇总';
    case 'explainability':
      return '解释性';
    case 'packaging':
      return '封装';
    case 'history_archive':
      return '归档';
    case 'sequencing':
      return '序列构造';
    case 'model_init':
      return '模型初始化';
    case 'training':
      return '训练';
    case 'vertex_queue':
      return 'Vertex 排队';
    case 'vertex_training':
      return 'Vertex 训练';
    case 'vertex_finalize':
      return 'Vertex 回传';
    case 'artifact_upload':
      return '产物上传';
    case 'fetch_documents':
      return '取文档';
    case 'reset_collection':
      return '重建集合';
    case 'parsing':
      return '切片';
    case 'embedding':
      return '向量化';
    case 'completed':
      return '完成';
    case 'failed':
      return '失败';
    default:
      return '进度';
  }
}

class _EventRow extends StatelessWidget {
  const _EventRow({
    required this.job,
    required this.event,
    required this.isLast,
  });

  final JobRecord job;
  final JobEvent event;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final phaseLabel = _phaseLabel(event.phase);
    final statusColor = _statusColor(event.status);
    final computeSummary = buildComputeSummaryLine(
      event.metrics.isNotEmpty
          ? event.metrics
          : event.step?.metrics ?? const {},
    );

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 20,
          child: Column(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: statusColor,
                  shape: BoxShape.circle,
                ),
              ),
              if (!isLast)
                Container(width: 2, height: 46, color: AppColors.border),
            ],
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: statusColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(
                          AppDecorations.radiusFull,
                        ),
                      ),
                      child: Text(
                        phaseLabel,
                        style: AppTextStyles.labelMedium.copyWith(
                          color: statusColor,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Text(
                      _formatTimestamp(event.timestamp),
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    Text(
                      '${event.progress}%',
                      style: AppTextStyles.labelMedium.copyWith(
                        color: AppColors.textMuted,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  buildJobEventMessage(job, event),
                  style: AppTextStyles.bodyMedium,
                ),
                if (computeSummary.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Compute · $computeSummary',
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'queued':
        return AppColors.primary;
      case 'running':
        return AppColors.cta;
      case 'succeeded':
        return AppColors.success;
      case 'failed':
        return AppColors.error;
      default:
        return AppColors.textSecondary;
    }
  }

  String _phaseLabel(String value) {
    switch (value) {
      case 'queued':
        return '排队';
      case 'started':
        return '启动';
      case 'dataset':
        return '数据加载';
      case 'basic_analysis':
        return '基础剖析';
      case 'model_metadata':
        return '模型元数据';
      case 'quality':
        return '质量检查';
      case 'correlation':
        return '相关性';
      case 'statistical':
        return '统计检验';
      case 'forecast':
        return '预测';
      case 'solver':
        return '求解';
      case 'aggregation':
        return '汇总';
      case 'explainability':
        return '解释性';
      case 'packaging':
        return '封装';
      case 'history_archive':
        return '归档';
      case 'sequencing':
        return '序列构造';
      case 'model_init':
        return '模型初始化';
      case 'training':
        return '训练';
      case 'vertex_queue':
        return 'Vertex 排队';
      case 'vertex_training':
        return 'Vertex 训练';
      case 'vertex_finalize':
        return 'Vertex 回传';
      case 'artifact_upload':
        return '产物上传';
      case 'fetch_documents':
        return '取文档';
      case 'reset_collection':
        return '重建集合';
      case 'parsing':
        return '切片';
      case 'embedding':
        return '向量化';
      case 'compute_rollout_prepare':
        return '治理预检';
      case 'compute_rollout_apply':
        return '治理应用';
      case 'compute_benchmark_prepare':
        return '准备 benchmark';
      case 'compute_benchmark_run':
        return '执行 benchmark';
      case 'compute_benchmark_publish':
        return '发布 benchmark';
      case 'completed':
        return '完成';
      case 'failed':
        return '失败';
      default:
        return '进度';
    }
  }

  String _formatTimestamp(DateTime? value) {
    if (value == null) {
      return '时间未知';
    }
    return DateFormat('MM-dd HH:mm:ss').format(value.toLocal());
  }
}
