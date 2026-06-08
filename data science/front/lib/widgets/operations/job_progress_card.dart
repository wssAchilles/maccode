/// 作业进度卡
library;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import '../../utils/external_link.dart';
import '../../utils/job_presentation.dart';
import '../common/glass_card.dart';

class JobProgressCard extends StatelessWidget {
  const JobProgressCard({
    super.key,
    required this.job,
    this.compact = false,
    this.onOpenDetails,
  });

  final JobRecord job;
  final bool compact;
  final VoidCallback? onOpenDetails;

  @override
  Widget build(BuildContext context) {
    final tone = _JobTone.fromStatus(job.status);
    final latestEvent = job.latestEvent;
    final currentStep = job.currentStep;
    if (compact) {
      return _CompactJobProgressRow(
        job: job,
        tone: tone,
        latestEvent: latestEvent,
        onOpenDetails: onOpenDetails,
      );
    }

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
              Flexible(
                child: Text(
                  job.displayTitle,
                  textAlign: TextAlign.end,
                  style: AppTextStyles.labelLarge.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(buildJobPrimaryText(job), style: AppTextStyles.h4),
          if (currentStep != null) ...[
            const SizedBox(height: 8),
            Text(
              '当前步骤 · ${_JobPhaseChip.phaseLabel(currentStep.phase)} · ${currentStep.toolName}',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
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
          if (job.type == 'ml_train' &&
              (job.trainingBackend != null ||
                  job.externalJobState != null)) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (job.trainingBackend != null)
                  _InfoChip(
                    label: job.isVertexTraining ? 'Vertex AI' : 'Legacy',
                    accent: job.isVertexTraining
                        ? AppColors.primary
                        : AppColors.textSecondary,
                  ),
                if ((job.externalJobState ?? '').isNotEmpty)
                  _InfoChip(
                    label: _externalStateLabel(job.externalJobState!),
                    accent: AppColors.cta,
                  ),
              ],
            ),
          ],
          if (job.artifacts.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              '产物 ${job.artifacts.length} 项',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
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
          if (onOpenDetails != null) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: onOpenDetails,
                icon: const Icon(Icons.travel_explore_rounded),
                label: const Text('查看运行详情'),
              ),
            ),
          ],
          if ((job.externalJobConsoleUrl ?? '').isNotEmpty) ...[
            const SizedBox(height: 4),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () {
                  final url = job.externalJobConsoleUrl;
                  if (url != null) {
                    openExternalLink(url);
                  }
                },
                icon: const Icon(Icons.open_in_new_rounded),
                label: const Text('打开 Vertex 作业'),
              ),
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

class _CompactJobProgressRow extends StatelessWidget {
  const _CompactJobProgressRow({
    required this.job,
    required this.tone,
    required this.latestEvent,
    this.onOpenDetails,
  });

  final JobRecord job;
  final _JobTone tone;
  final JobEvent? latestEvent;
  final VoidCallback? onOpenDetails;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: tone.foreground.withValues(alpha: 0.12)),
      ),
      child: Row(
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: tone.foreground,
              borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 5,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  buildJobPrimaryText(job),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTextStyles.labelLarge,
                ),
                const SizedBox(height: 3),
                Text(
                  latestEvent == null
                      ? job.displayTitle
                      : '${_JobPhaseChip.phaseLabel(latestEvent!.phase)} · ${buildJobEventMessage(job, latestEvent!)}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTextStyles.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          SizedBox(
            width: 120,
            child: LinearProgressIndicator(
              value: (job.progress.clamp(0, 100)) / 100,
              minHeight: 6,
              borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
              backgroundColor: AppColors.surface,
              color: tone.foreground,
            ),
          ),
          const SizedBox(width: 10),
          SizedBox(
            width: 42,
            child: Text(
              '${job.progress}%',
              textAlign: TextAlign.end,
              style: AppTextStyles.labelMedium,
            ),
          ),
          if (onOpenDetails != null) ...[
            const SizedBox(width: 8),
            IconButton(
              onPressed: onOpenDetails,
              tooltip: '查看运行详情',
              icon: const Icon(Icons.travel_explore_rounded),
              visualDensity: VisualDensity.compact,
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelMedium.copyWith(
          color: accent,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

String _externalStateLabel(String state) {
  switch (state) {
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
    default:
      return state;
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
        phaseLabel(phase),
        style: AppTextStyles.labelMedium.copyWith(
          color: tone.foreground,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  static String phaseLabel(String value) {
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
      case 'awaiting_approval':
        return const _JobTone(
          label: '待审批',
          foreground: AppColors.warning,
          background: Color(0xFFFFF4E5),
          icon: Icons.pending_actions_rounded,
        );
      case 'dispatching':
        return const _JobTone(
          label: '调度中',
          foreground: AppColors.primary,
          background: AppColors.infoLight,
          icon: Icons.route_rounded,
        );
      case 'retrying':
      case 'running':
        return _JobTone(
          label: status == 'retrying' ? '重试中' : '进行中',
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
