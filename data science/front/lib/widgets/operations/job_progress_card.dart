/// 作业进度卡
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import '../../utils/job_presentation.dart';
import '../common/glass_card.dart';

class JobProgressCard extends StatelessWidget {
  const JobProgressCard({super.key, required this.job, this.compact = false});

  final JobRecord job;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final tone = _JobTone.fromStatus(job.status);
    final latestEvent = job.latestEvent;
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: tone.background,
                  borderRadius: BorderRadius.circular(
                    AppDecorations.radiusFull,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(tone.icon, size: 14, color: tone.foreground),
                    const SizedBox(width: 6),
                    Text(
                      tone.label,
                      style: AppTextStyles.labelMedium.copyWith(
                        color: tone.foreground,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              Text(
                job.displayTitle,
                style: AppTextStyles.labelLarge.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            buildJobPrimaryText(job),
            style: AppTextStyles.h4,
          ),
          if (latestEvent != null) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                _JobPhaseChip(
                  phase: latestEvent.phase,
                  status: latestEvent.status,
                ),
                Text(
                  _formatTime(latestEvent.timestamp),
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: (job.progress.clamp(0, 100)) / 100,
            minHeight: 8,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            backgroundColor: AppColors.surfaceVariant,
            color: tone.foreground,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text('${job.progress}%', style: AppTextStyles.labelMedium),
              const Spacer(),
              if (!compact)
                Text(
                  _formatTime(job.submittedAt),
                  style: AppTextStyles.bodySmall,
                ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '尝试 ${job.attemptCount}/${job.maxAttempts}'
            '${job.retryable ? ' · 可重试' : ''}',
            style: AppTextStyles.bodySmall.copyWith(
              color: job.retryable ? AppColors.warning : AppColors.textMuted,
            ),
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

  String _formatTime(DateTime? value) {
    if (value == null) {
      return '时间未知';
    }
    return DateFormat('MM-dd HH:mm').format(value.toLocal());
  }
}

class _JobPhaseChip extends StatelessWidget {
  const _JobPhaseChip({required this.phase, required this.status});

  final String phase;
  final String status;

  @override
  Widget build(BuildContext context) {
    final tone = _JobTone.fromStatus(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: tone.background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        _phaseLabel(phase),
        style: AppTextStyles.labelMedium.copyWith(
          color: tone.foreground,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
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
}

class _JobTone {
  const _JobTone({
    required this.label,
    required this.foreground,
    required this.background,
    required this.icon,
  });

  final String label;
  final Color foreground;
  final Color background;
  final IconData icon;

  factory _JobTone.fromStatus(String status) {
    switch (status) {
      case 'queued':
        return const _JobTone(
          label: '已排队',
          foreground: AppColors.primary,
          background: AppColors.infoLight,
          icon: Icons.schedule_rounded,
        );
      case 'running':
        return const _JobTone(
          label: '进行中',
          foreground: AppColors.cta,
          background: Color(0xFFFFEDD5),
          icon: Icons.autorenew_rounded,
        );
      case 'succeeded':
        return const _JobTone(
          label: '已完成',
          foreground: AppColors.success,
          background: AppColors.successLight,
          icon: Icons.check_circle_rounded,
        );
      case 'failed':
        return const _JobTone(
          label: '失败',
          foreground: AppColors.error,
          background: AppColors.errorLight,
          icon: Icons.error_rounded,
        );
      default:
        return const _JobTone(
          label: '已取消',
          foreground: AppColors.textSecondary,
          background: AppColors.surfaceVariant,
          icon: Icons.cancel_outlined,
        );
    }
  }
}
