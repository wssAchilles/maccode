/// 工业驾驶舱概览页
library;

import 'package:flutter/material.dart';

import '../config/app_theme.dart';
import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../utils/responsive_helper.dart';
import '../viewmodels/dashboard_view_model.dart';
import '../widgets/common/glass_card.dart';
import '../widgets/operations/alert_panel.dart';
import '../widgets/operations/dataset_asset_card.dart';
import '../widgets/operations/job_activity_list.dart';
import '../widgets/operations/metric_card.dart';
import '../widgets/operations/model_status_card.dart';
import '../widgets/operations/quick_actions_section.dart';
import '../widgets/operations/system_status_strip.dart';
import '../widgets/responsive_wrapper.dart';

class OperationsHubScreen extends StatefulWidget {
  const OperationsHubScreen({
    super.key,
    required this.viewModel,
    required this.onNavigateToTab,
    this.embedded = false,
  });

  final DashboardViewModel viewModel;
  final ValueChanged<int> onNavigateToTab;
  final bool embedded;

  @override
  State<OperationsHubScreen> createState() => _OperationsHubScreenState();
}

class _OperationsHubScreenState extends State<OperationsHubScreen> {
  @override
  void initState() {
    super.initState();
    widget.viewModel.initialize();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.viewModel,
      builder: (context, _) {
        final summary = widget.viewModel.summary;
        final content = RefreshIndicator(
          onRefresh: widget.viewModel.loadSummary,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              if (!widget.embedded)
                SliverAppBar(
                  pinned: true,
                  expandedHeight: 120,
                  backgroundColor: AppColors.surface,
                  foregroundColor: AppColors.textPrimary,
                  flexibleSpace: FlexibleSpaceBar(
                    titlePadding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                    title: Text('Operations Hub', style: AppTextStyles.h3),
                    background: Container(
                      decoration: const BoxDecoration(
                        gradient: AppColors.backgroundGradient,
                      ),
                    ),
                  ),
                ),
              if (!ResponsiveHelper.isDesktop(context) &&
                  summary != null &&
                  !widget.embedded)
                SliverToBoxAdapter(
                  child: SystemStatusStrip(items: summary.systemStatus),
                ),
              SliverToBoxAdapter(
                child: ResponsiveWrapper(
                  child: Padding(
                    padding: ResponsiveHelper.getPagePadding(context),
                    child: _buildBody(summary),
                  ),
                ),
              ),
            ],
          ),
        );

        if (widget.embedded) {
          return content;
        }

        return Scaffold(backgroundColor: AppColors.background, body: content);
      },
    );
  }

  Widget _buildBody(DashboardSummary? summary) {
    if (widget.viewModel.isLoading && summary == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 120),
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (widget.viewModel.errorMessage != null && summary == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 120),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                widget.viewModel.errorMessage!,
                style: AppTextStyles.bodyMedium,
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: widget.viewModel.loadSummary,
                child: const Text('重试'),
              ),
            ],
          ),
        ),
      );
    }

    final safeSummary = summary;
    if (safeSummary == null) {
      return const SizedBox.shrink();
    }

    final modelStatus = safeSummary.systemStatus
        .cast<SystemStatusItem?>()
        .firstWhere((item) => item?.key == 'model', orElse: () => null);
    final ragStatus = safeSummary.systemStatus
        .cast<SystemStatusItem?>()
        .firstWhere((item) => item?.key == 'rag', orElse: () => null);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHero(safeSummary),
        const SizedBox(height: 20),
        _buildMetrics(safeSummary.kpis),
        const SizedBox(height: 20),
        QuickActionsSection(
          actions: [
            QuickActionItem(
              label: '上传并分析数据',
              icon: Icons.upload_file_rounded,
              emphasis: true,
              onTap: () => widget.onNavigateToTab(2),
            ),
            QuickActionItem(
              label: '运行能源优化',
              icon: Icons.bolt_rounded,
              onTap: () => widget.onNavigateToTab(1),
            ),
            QuickActionItem(
              label: '开始模型训练',
              icon: Icons.model_training_rounded,
              onTap: () => widget.onNavigateToTab(3),
            ),
            QuickActionItem(
              label: '构建知识库',
              icon: Icons.auto_awesome_rounded,
              onTap: () => widget.onNavigateToTab(3),
            ),
            QuickActionItem(
              label: '查看历史与审计',
              icon: Icons.fact_check_rounded,
              onTap: () => widget.onNavigateToTab(4),
            ),
          ],
        ),
        const SizedBox(height: 20),
        LayoutBuilder(
          builder: (context, constraints) {
            final stacked = constraints.maxWidth < 1040;
            final left = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _SectionTitle(title: '最近任务', subtitle: '进行中与最近完成作业'),
                const SizedBox(height: 12),
                JobActivityList(
                  jobs: safeSummary.recentJobs,
                  emptyMessage: '暂无最近任务，提交优化、训练或知识库构建后会出现在这里。',
                ),
                const SizedBox(height: 20),
                _SectionTitle(title: '最近数据资产', subtitle: '最近完成分析的数据集'),
                const SizedBox(height: 12),
                if (safeSummary.recentAssets.isEmpty)
                  const _EmptySection(message: '暂无近期数据资产')
                else
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: safeSummary.recentAssets
                        .map(
                          (asset) => SizedBox(
                            width: stacked ? double.infinity : 260,
                            child: DatasetAssetCard(asset: asset),
                          ),
                        )
                        .toList(growable: false),
                  ),
                const SizedBox(height: 20),
                _SectionTitle(title: '最近活动', subtitle: '关键审计动作与系统轨迹'),
                const SizedBox(height: 12),
                if (safeSummary.recentHistory.isEmpty)
                  const _EmptySection(message: '暂无最近活动')
                else
                  _RecentActivityFeed(items: safeSummary.recentHistory),
              ],
            );

            final right = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _SectionTitle(title: '系统提醒', subtitle: '依赖、失败任务与数据空缺'),
                const SizedBox(height: 12),
                if (safeSummary.alerts.isEmpty)
                  const _EmptySection(message: '当前无高优先级告警')
                else
                  Column(
                    children: safeSummary.alerts
                        .map(
                          (alert) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: AlertPanel(alert: alert),
                          ),
                        )
                        .toList(growable: false),
                  ),
                const SizedBox(height: 20),
                _SectionTitle(title: '模型与知识状态', subtitle: '核心服务可用性'),
                const SizedBox(height: 12),
                if (modelStatus != null)
                  ModelStatusCard(
                    title: '负载预测模型',
                    status: modelStatus,
                    subtitle: '能源优化和驾驶舱预测依赖该模型。',
                  ),
                if (modelStatus != null && ragStatus != null)
                  const SizedBox(height: 12),
                if (ragStatus != null)
                  ModelStatusCard(
                    title: 'RAG 知识服务',
                    status: ragStatus,
                    subtitle: '问答和文档检索依赖知识库构建结果。',
                  ),
              ],
            );

            if (stacked) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [left, const SizedBox(height: 20), right],
              );
            }

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(flex: 7, child: left),
                const SizedBox(width: 20),
                Expanded(flex: 5, child: right),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildHero(DashboardSummary summary) {
    return GlassCard(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('工业能源与 AI 驾驶舱', style: AppTextStyles.h2),
          const SizedBox(height: 10),
          Text(
            '统一查看系统状态、最近任务、数据资产和风险提醒。概览页只展示当前最关键的运行信号。',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _HeroStat(label: '近 24h 任务', value: '${summary.kpis.jobs24h}'),
              _HeroStat(label: '失败任务', value: '${summary.kpis.failedJobs}'),
              _HeroStat(label: '最近分析', value: '${summary.kpis.analysisCount}'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetrics(DashboardKpis kpis) {
    final cards = [
      MetricCard(
        label: '数据集数',
        value: '${kpis.datasetCount}',
        icon: Icons.dataset_rounded,
        supportingText: '最近沉淀的数据资产',
      ),
      MetricCard(
        label: '分析次数',
        value: '${kpis.analysisCount}',
        icon: Icons.analytics_rounded,
        supportingText: '历史分析记录总量',
      ),
      MetricCard(
        label: '模型数量',
        value: '${kpis.modelCount}',
        icon: Icons.memory_rounded,
        supportingText: '最近训练产生的模型',
      ),
      MetricCard(
        label: '24h 作业数',
        value: '${kpis.jobs24h}',
        icon: Icons.schedule_rounded,
        supportingText: '近一天执行任务',
      ),
      MetricCard(
        label: '失败作业',
        value: '${kpis.failedJobs}',
        icon: Icons.report_problem_rounded,
        supportingText: '需要排查的失败项',
        emphasis: kpis.failedJobs > 0,
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final isDesktop = constraints.maxWidth >= 1100;
        final width = isDesktop ? (constraints.maxWidth - 48) / 5 : 240.0;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: cards
              .map((card) => SizedBox(width: width, child: card))
              .toList(growable: false),
        );
      },
    );
  }
}

class _HeroStat extends StatelessWidget {
  const _HeroStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTextStyles.labelMedium),
          const SizedBox(height: 6),
          Text(value, style: AppTextStyles.h4),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: AppTextStyles.h4),
        const SizedBox(height: 4),
        Text(subtitle, style: AppTextStyles.bodySmall),
      ],
    );
  }
}

class _EmptySection extends StatelessWidget {
  const _EmptySection({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(message, style: AppTextStyles.bodyMedium),
    );
  }
}

class _RecentActivityFeed extends StatelessWidget {
  const _RecentActivityFeed({required this.items});

  final List<AuditActivity> items;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: items
            .map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _ActivityRow(item: item),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _ActivityRow extends StatelessWidget {
  const _ActivityRow({required this.item});

  final AuditActivity item;

  @override
  Widget build(BuildContext context) {
    final color = switch (item.severity) {
      'error' => AppColors.error,
      'warning' => AppColors.warning,
      _ => AppColors.primary,
    };
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 10,
          height: 10,
          margin: const EdgeInsets.only(top: 4),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.title, style: AppTextStyles.labelLarge),
              const SizedBox(height: 4),
              Text(
                '${item.source} · ${item.status}',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
