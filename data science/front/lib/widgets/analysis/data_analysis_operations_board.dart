/// 数据分析运营态面板
library;

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/analysis_result.dart';
import '../../models/job_record.dart';
import '../common/glass_card.dart';

class DataAnalysisOperationsBoard extends StatelessWidget {
  const DataAnalysisOperationsBoard({
    super.key,
    required this.currentUser,
    required this.pickedFile,
    required this.analysisResult,
    required this.saveToStorage,
    required this.latestStoragePath,
    required this.jobs,
    required this.jobsLoading,
    required this.jobErrorMessage,
  });

  final User? currentUser;
  final PlatformFile? pickedFile;
  final AnalysisResult? analysisResult;
  final bool saveToStorage;
  final String? latestStoragePath;
  final List<JobRecord> jobs;
  final bool jobsLoading;
  final String? jobErrorMessage;

  @override
  Widget build(BuildContext context) {
    final latestJob = jobs.isEmpty ? null : jobs.first;
    final schemaMix = _SchemaMix.fromResult(analysisResult);
    final qualityMetrics = analysisResult?.qualityAnalysis?.qualityMetrics;
    final duplicateCheck = analysisResult?.qualityAnalysis?.duplicateCheck;
    final qualityScore = analysisResult?.qualityAnalysis?.qualityScore;
    final highRiskColumns =
        analysisResult?.qualityAnalysis?.highRiskColumns?.length ?? 0;
    final runningJobs = jobs.where((job) => job.isRunning).length;
    final failedJobs = jobs.where((job) => job.status == 'failed').length;
    final completedJobs = jobs.where((job) => job.status == 'succeeded').length;
    final assetReady =
        latestStoragePath != null && latestStoragePath!.trim().isNotEmpty;
    final trainingReady = assetReady && schemaMix.numericCount > 0;
    final ragReady = assetReady && analysisResult != null;
    final backgroundRecommended =
        (pickedFile?.size ?? 0) >= 5 * 1024 * 1024 ||
        (analysisResult?.basicInfo.rows ?? 0) >= 50000;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('运营态概览', style: AppTextStyles.h4),
        const SizedBox(height: 6),
        Text(
          '把执行策略、任务健康、资产沉淀和 AI 准备度放到同一视图，减少在分析完成后的额外判断。',
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final isCompact = constraints.maxWidth < 1180;
            final cards = [
              _OperationsCard(
                title: '执行策略',
                subtitle: '根据文件体量和当前结果推荐即时分析或后台任务模式。',
                accent: backgroundRecommended
                    ? AppColors.cta
                    : AppColors.primary,
                icon: backgroundRecommended
                    ? Icons.schedule_rounded
                    : Icons.bolt_rounded,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _MetricRow(
                      label: '推荐模式',
                      value: pickedFile == null
                          ? '等待选择数据集'
                          : backgroundRecommended
                          ? '后台分析任务'
                          : '即时分析',
                    ),
                    _MetricRow(
                      label: '文件体量',
                      value: pickedFile == null
                          ? '--'
                          : _formatBytes(pickedFile!.size),
                    ),
                    _MetricRow(
                      label: '当前规模',
                      value: analysisResult == null
                          ? '待分析后识别'
                          : '${analysisResult!.basicInfo.rows} 行 / '
                                '${analysisResult!.basicInfo.columns} 列',
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _StateBadge(
                          label: backgroundRecommended ? '推荐异步' : '即时可读',
                          tone: backgroundRecommended
                              ? _BadgeTone.cta
                              : _BadgeTone.info,
                        ),
                        _StateBadge(
                          label: saveToStorage ? '归档开启' : '仅当前会话',
                          tone: saveToStorage
                              ? _BadgeTone.success
                              : _BadgeTone.warning,
                        ),
                        _StateBadge(
                          label: currentUser == null ? '待登录' : '会话有效',
                          tone: currentUser == null
                              ? _BadgeTone.warning
                              : _BadgeTone.success,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              _OperationsCard(
                title: '任务健康',
                subtitle: '跟踪后台分析的运行状态、失败积压和最近阶段。',
                accent: failedJobs > 0 ? AppColors.warning : AppColors.success,
                icon: failedJobs > 0
                    ? Icons.warning_amber_rounded
                    : Icons.monitor_heart_rounded,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _MetricRow(label: '运行中', value: '$runningJobs'),
                    _MetricRow(label: '已完成', value: '$completedJobs'),
                    _MetricRow(label: '失败待看', value: '$failedJobs'),
                    _MetricRow(
                      label: '最近阶段',
                      value:
                          latestJob?.latestEvent?.message ??
                          latestJob?.statusMessage ??
                          (jobsLoading ? '正在刷新任务列表' : '暂无后台分析任务'),
                    ),
                    if (jobErrorMessage != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        jobErrorMessage!,
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.error,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              _OperationsCard(
                title: '资产路线',
                subtitle: '明确结果是否已沉淀为可复用资产，以及下一跳工作流。',
                accent: assetReady ? AppColors.primary : AppColors.warning,
                icon: assetReady ? Icons.route_rounded : Icons.route_outlined,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _MetricRow(
                      label: '资产状态',
                      value: assetReady ? '可复用' : '未形成可复用路径',
                    ),
                    _MetricRow(
                      label: 'Storage Path',
                      value: assetReady
                          ? _trimStoragePath(latestStoragePath!)
                          : '等待归档或后台任务完成',
                    ),
                    _MetricRow(
                      label: '历史链路',
                      value: saveToStorage ? '将写入历史与审计' : '本次不入历史',
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _StateBadge(
                          label: trainingReady ? '训练可接入' : '训练待准备',
                          tone: trainingReady
                              ? _BadgeTone.success
                              : _BadgeTone.warning,
                        ),
                        _StateBadge(
                          label: ragReady ? 'RAG 可接入' : 'RAG 待准备',
                          tone: ragReady ? _BadgeTone.info : _BadgeTone.warning,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              _OperationsCard(
                title: '数据资产质量',
                subtitle: '用 schema 构成和清洗风险评估是否适合继续进入 AI 流程。',
                accent: highRiskColumns > 0 ? AppColors.cta : AppColors.primary,
                icon: highRiskColumns > 0
                    ? Icons.dataset_linked_rounded
                    : Icons.fact_check_rounded,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _MetricRow(
                      label: 'Schema',
                      value: analysisResult == null
                          ? '待生成'
                          : '${schemaMix.numericCount} 数值 / '
                                '${schemaMix.categoricalCount} 类别 / '
                                '${schemaMix.datetimeCount} 时间',
                    ),
                    _MetricRow(
                      label: '质量评分',
                      value: qualityScore == null
                          ? '待质量检查'
                          : '${qualityScore.toStringAsFixed(0)} / 100',
                    ),
                    _MetricRow(
                      label: '缺失率',
                      value: qualityMetrics == null
                          ? '--'
                          : _formatPercentage(qualityMetrics.missingRate),
                    ),
                    _MetricRow(
                      label: '重复行',
                      value: duplicateCheck == null
                          ? '--'
                          : '${duplicateCheck.count} '
                                '(${_formatPercentage(duplicateCheck.percentage)})',
                    ),
                    _MetricRow(label: '高风险列', value: '$highRiskColumns'),
                  ],
                ),
              ),
            ];

            if (isCompact) {
              return Column(
                children: [
                  for (var i = 0; i < cards.length; i++) ...[
                    cards[i],
                    if (i < cards.length - 1) const SizedBox(height: 12),
                  ],
                ],
              );
            }

            return Column(
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: cards[0]),
                    const SizedBox(width: 12),
                    Expanded(child: cards[1]),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: cards[2]),
                    const SizedBox(width: 12),
                    Expanded(child: cards[3]),
                  ],
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _OperationsCard extends StatelessWidget {
  const _OperationsCard({
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.icon,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Color accent;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
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
          const SizedBox(height: 16),
          child,
        ],
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.label, required this.value});

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
            width: 88,
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

enum _BadgeTone { success, warning, info, cta }

class _StateBadge extends StatelessWidget {
  const _StateBadge({required this.label, required this.tone});

  final String label;
  final _BadgeTone tone;

  @override
  Widget build(BuildContext context) {
    final colors = switch (tone) {
      _BadgeTone.success => (AppColors.success, AppColors.successLight),
      _BadgeTone.warning => (AppColors.warning, AppColors.warningLight),
      _BadgeTone.info => (AppColors.primary, AppColors.infoLight),
      _BadgeTone.cta => (AppColors.cta, const Color(0xFFFFEDD5)),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: colors.$2,
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelSmall.copyWith(
          color: colors.$1,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _SchemaMix {
  const _SchemaMix({
    required this.numericCount,
    required this.categoricalCount,
    required this.datetimeCount,
  });

  final int numericCount;
  final int categoricalCount;
  final int datetimeCount;

  factory _SchemaMix.fromResult(AnalysisResult? result) {
    if (result == null) {
      return const _SchemaMix(
        numericCount: 0,
        categoricalCount: 0,
        datetimeCount: 0,
      );
    }

    var numeric = 0;
    var categorical = 0;
    var datetime = 0;

    for (final type in result.basicInfo.columnTypes.values) {
      final normalized = type.toLowerCase();
      if (_isNumericType(normalized)) {
        numeric += 1;
      } else if (_isDatetimeType(normalized)) {
        datetime += 1;
      } else {
        categorical += 1;
      }
    }

    return _SchemaMix(
      numericCount: numeric,
      categoricalCount: categorical,
      datetimeCount: datetime,
    );
  }

  static bool _isNumericType(String value) {
    return value.contains('int') ||
        value.contains('float') ||
        value.contains('double') ||
        value.contains('decimal') ||
        value.contains('number');
  }

  static bool _isDatetimeType(String value) {
    return value.contains('date') ||
        value.contains('time') ||
        value.contains('timestamp');
  }
}

String _formatBytes(int bytes) {
  if (bytes <= 0) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB'];
  var value = bytes.toDouble();
  var unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  final digits = value >= 100
      ? 0
      : value >= 10
      ? 1
      : 2;
  return '${value.toStringAsFixed(digits)} ${units[unitIndex]}';
}

String _formatPercentage(double value) {
  final normalized = value <= 1 ? value * 100 : value;
  return '${normalized.toStringAsFixed(normalized >= 10 ? 1 : 2)}%';
}

String _trimStoragePath(String value) {
  if (value.length <= 32) {
    return value;
  }
  return '${value.substring(0, 14)}...${value.substring(value.length - 14)}';
}
