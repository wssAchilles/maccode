/// 作业阶段时间线
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import '../../utils/job_presentation.dart';
import '../common/glass_card.dart';

class JobEventTimeline extends StatelessWidget {
  const JobEventTimeline({
    super.key,
    required this.job,
    this.title = '任务阶段轨迹',
    this.emptyMessage = '等待任务事件写入。',
    this.maxVisibleEvents = 8,
    this.onRetry,
  });

  final JobRecord job;
  final String title;
  final String emptyMessage;
  final int maxVisibleEvents;
  final VoidCallback? onRetry;

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
                  if (job.retryable && onRetry != null) ...[
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: onRetry,
                      icon: const Icon(Icons.restart_alt_rounded),
                      label: const Text('重试任务'),
                    ),
                  ],
                ],
              ),
            ],
          ),
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
      case 'running':
        return ('进行中', const Color(0xFFFFEDD5), AppColors.cta);
      case 'succeeded':
        return ('已完成', AppColors.successLight, AppColors.success);
      case 'failed':
        return ('失败', AppColors.errorLight, AppColors.error);
      default:
        return ('已取消', AppColors.surfaceVariant, AppColors.textSecondary);
    }
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

  String _formatTimestamp(DateTime? value) {
    if (value == null) {
      return '时间未知';
    }
    return DateFormat('MM-dd HH:mm:ss').format(value.toLocal());
  }
}
