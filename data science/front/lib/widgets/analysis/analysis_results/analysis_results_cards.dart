part of '../analysis_results_section.dart';

class _ResultSummaryBanner extends StatelessWidget {
  const _ResultSummaryBanner({
    required this.result,
    this.chain,
    this.continuationContext,
  });

  final AnalysisResult result;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final qualityScore = result.qualityAnalysis?.qualityScore;
    final highRiskCount = result.qualityAnalysis?.highRiskColumns?.length ?? 0;
    final correlationPairs = result.correlations?.correlations?.length ?? 0;
    final normalColumns =
        result.statisticalTests?.summary?.normalDistributionCount ?? 0;

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AssetChainSectionHeader(
            title: '分析结果总览',
            subtitle: '先看质量与结构，再深入相关性和统计检验。这里保留的是最适合快速判断数据是否可进入下一阶段的信号。',
            chain: chain,
            continuationContext: continuationContext,
            icon: Icons.assessment_rounded,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _AnalysisSummaryItem(
                label: '数据规模',
                value: '${result.basicInfo.rows} x ${result.basicInfo.columns}',
                icon: Icons.grid_view_rounded,
                color: AppColors.primary,
                background: AppColors.infoLight,
              ),
              _AnalysisSummaryItem(
                label: '质量分',
                value: qualityScore == null
                    ? '--'
                    : '${qualityScore.toStringAsFixed(0)} / 100',
                icon: Icons.health_and_safety_rounded,
                color: qualityScore != null && qualityScore < 80
                    ? AppColors.warning
                    : AppColors.success,
                background: qualityScore != null && qualityScore < 80
                    ? AppColors.warningLight
                    : AppColors.successLight,
              ),
              _AnalysisSummaryItem(
                label: '相关性对',
                value: '$correlationPairs',
                icon: Icons.hub_rounded,
                color: AppColors.cta,
                background: const Color(0xFFFFEDD5),
              ),
              _AnalysisSummaryItem(
                label: '近似正态列',
                value: '$normalColumns',
                icon: Icons.analytics_rounded,
                color: highRiskCount > 0
                    ? AppColors.warning
                    : AppColors.textPrimary,
                background: highRiskCount > 0
                    ? AppColors.warningLight
                    : AppColors.surfaceVariant,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _BasicInfoCard extends StatelessWidget {
  const _BasicInfoCard({required this.result});

  final AnalysisResult result;

  @override
  Widget build(BuildContext context) {
    final basicInfo = result.basicInfo;

    return GlassCard(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.infoLight,
                  borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
                ),
                child: const Icon(
                  Icons.info_outline_rounded,
                  size: 20,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(width: 12),
              Text('数据结构概览', style: AppTextStyles.h4),
            ],
          ),
          const SizedBox(height: 16),
          _AnalysisInfoRow(label: '行数', value: '${basicInfo.rows}'),
          _AnalysisInfoRow(label: '列数', value: '${basicInfo.columns}'),
          const SizedBox(height: 14),
          Text('列名与类型', style: AppTextStyles.labelLarge),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: basicInfo.columnNames
                .map(
                  (column) => Tooltip(
                    message:
                        '类型: ${basicInfo.columnTypes[column] ?? "unknown"}',
                    child: Chip(
                      avatar: Icon(
                        _columnTypeIcon(basicInfo.columnTypes[column]),
                        size: 16,
                      ),
                      label: Text(column),
                      backgroundColor: _columnTypeColor(
                        basicInfo.columnTypes[column],
                      ),
                      labelStyle: AppTextStyles.labelMedium,
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _AssetConsoleSection extends StatelessWidget {
  const _AssetConsoleSection({
    required this.result,
    this.chain,
    this.continuationContext,
  });

  final AnalysisResult result;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final focusArea = _assetConsoleFocusArea(chain);
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1320;
        final cards = [
          _consoleShell(
            highlighted: focusArea == 'schema',
            color: AppColors.primary,
            child: _SchemaTopologyCard(
              result: result,
              chain: focusArea == 'schema' ? chain : null,
              continuationContext: focusArea == 'schema'
                  ? continuationContext
                  : null,
            ),
          ),
          _consoleShell(
            highlighted: focusArea == 'distribution',
            color: AppColors.cta,
            child: _FieldDistributionCard(
              result: result,
              chain: focusArea == 'distribution' ? chain : null,
              continuationContext: focusArea == 'distribution'
                  ? continuationContext
                  : null,
            ),
          ),
          _consoleShell(
            highlighted: focusArea == 'risk',
            color: AppColors.warning,
            child: _DataRiskDigestCard(
              result: result,
              chain: focusArea == 'risk' ? chain : null,
              continuationContext: focusArea == 'risk'
                  ? continuationContext
                  : null,
            ),
          ),
          _consoleShell(
            highlighted: focusArea == 'actions',
            color: AppColors.cta,
            child: _NextActionsCard(
              result: result,
              chain: focusArea == 'actions' ? chain : null,
              continuationContext: focusArea == 'actions'
                  ? continuationContext
                  : null,
            ),
          ),
        ];

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AssetChainSectionHeader(
              title: 'Asset Console',
              subtitle: '把 schema、字段分布、风险摘要和下一步动作收成同一层，便于按当前数据链路继续判断。',
              chain: chain,
              continuationContext: continuationContext,
              icon: Icons.inventory_2_rounded,
            ),
            const SizedBox(height: 12),
            if (compact)
              Column(
                children: [
                  for (var i = 0; i < cards.length; i++) ...[
                    cards[i],
                    if (i < cards.length - 1) const SizedBox(height: 12),
                  ],
                ],
              )
            else
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: cards[0]),
                  const SizedBox(width: 12),
                  Expanded(child: cards[1]),
                  const SizedBox(width: 12),
                  Expanded(child: cards[2]),
                  const SizedBox(width: 12),
                  Expanded(child: cards[3]),
                ],
              ),
          ],
        );
      },
    );
  }
}

class _SchemaTopologyCard extends StatelessWidget {
  const _SchemaTopologyCard({
    required this.result,
    this.chain,
    this.continuationContext,
  });

  final AnalysisResult result;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final mix = _ResultSchemaMix.fromResult(result);
    final highlightedColumns = result.basicInfo.columnNames.take(6).toList();

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ConsoleCardHeader(
            title: 'Schema Topology',
            subtitle: '快速判断数据集的字段构成和可建模性。',
            accent: AppColors.primary,
            icon: Icons.account_tree_rounded,
            chain: chain,
            continuationContext: continuationContext,
          ),
          const SizedBox(height: 14),
          _AnalysisInfoRow(label: '数值字段', value: '${mix.numericCount}'),
          _AnalysisInfoRow(label: '类别字段', value: '${mix.categoricalCount}'),
          _AnalysisInfoRow(label: '时间字段', value: '${mix.datetimeCount}'),
          const SizedBox(height: 12),
          Text('重点字段', style: AppTextStyles.labelLarge),
          const SizedBox(height: 8),
          if (highlightedColumns.isEmpty)
            Text(
              '分析完成后显示字段摘要',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: highlightedColumns
                  .map(
                    (column) => Chip(
                      label: Text(column),
                      avatar: Icon(
                        _columnTypeIcon(result.basicInfo.columnTypes[column]),
                        size: 16,
                      ),
                      backgroundColor: _columnTypeColor(
                        result.basicInfo.columnTypes[column],
                      ),
                    ),
                  )
                  .toList(),
            ),
        ],
      ),
    );
  }
}

class _FieldDistributionCard extends StatelessWidget {
  const _FieldDistributionCard({
    required this.result,
    this.chain,
    this.continuationContext,
  });

  final AnalysisResult result;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final mix = _ResultSchemaMix.fromResult(result);
    final total = (mix.numericCount + mix.categoricalCount + mix.datetimeCount)
        .clamp(1, 1 << 20);
    final numericRatio = mix.numericCount / total;
    final categoricalRatio = mix.categoricalCount / total;
    final datetimeRatio = mix.datetimeCount / total;

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ConsoleCardHeader(
            title: 'Field Distribution',
            subtitle: '用字段配比判断资产更偏建模、索引还是治理准备。',
            accent: AppColors.cta,
            icon: Icons.pie_chart_outline_rounded,
            chain: chain,
            continuationContext: continuationContext,
          ),
          const SizedBox(height: 14),
          _DistributionBar(
            label: '数值字段',
            ratio: numericRatio,
            value: '${mix.numericCount}',
            color: AppColors.primary,
            background: AppColors.infoLight,
          ),
          const SizedBox(height: 10),
          _DistributionBar(
            label: '类别字段',
            ratio: categoricalRatio,
            value: '${mix.categoricalCount}',
            color: AppColors.success,
            background: AppColors.successLight,
          ),
          const SizedBox(height: 10),
          _DistributionBar(
            label: '时间字段',
            ratio: datetimeRatio,
            value: '${mix.datetimeCount}',
            color: AppColors.cta,
            background: const Color(0xFFFFEDD5),
          ),
          const SizedBox(height: 14),
          _AnalysisInfoRow(label: '主导类型', value: _dominantSchemaLabel(mix)),
          _AnalysisInfoRow(label: '训练倾向', value: _trainingPosture(mix)),
          _AnalysisInfoRow(label: '知识倾向', value: _ragPosture(mix)),
        ],
      ),
    );
  }
}

class _DataRiskDigestCard extends StatelessWidget {
  const _DataRiskDigestCard({
    required this.result,
    this.chain,
    this.continuationContext,
  });

  final AnalysisResult result;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final quality = result.qualityAnalysis;
    final metrics = quality?.qualityMetrics;
    final duplicates = quality?.duplicateCheck;
    final qualityScore = quality?.qualityScore;
    final outlierCount = metrics?.totalOutliers ?? 0;
    final highRiskColumns = quality?.highRiskColumns?.length ?? 0;

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ConsoleCardHeader(
            title: 'Risk Digest',
            subtitle: '把缺失、重复、异常和高风险字段压成治理摘要。',
            accent: highRiskColumns > 0 ? AppColors.cta : AppColors.success,
            icon: highRiskColumns > 0
                ? Icons.warning_amber_rounded
                : Icons.verified_rounded,
            chain: chain,
            continuationContext: continuationContext,
          ),
          const SizedBox(height: 14),
          _AnalysisInfoRow(
            label: '质量评分',
            value: qualityScore == null
                ? '--'
                : '${qualityScore.toStringAsFixed(0)} / 100',
          ),
          _AnalysisInfoRow(
            label: '缺失率',
            value: metrics == null
                ? '--'
                : _formatResultPercentage(metrics.missingRate),
          ),
          _AnalysisInfoRow(
            label: '重复行',
            value: duplicates == null
                ? '--'
                : '${duplicates.count} '
                      '(${_formatResultPercentage(duplicates.percentage)})',
          ),
          _AnalysisInfoRow(label: '异常值', value: '$outlierCount'),
          _AnalysisInfoRow(label: '高风险列', value: '$highRiskColumns'),
          if (quality?.highRiskColumns?.isNotEmpty == true) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: quality!.highRiskColumns!
                  .take(4)
                  .map(
                    (column) => Chip(
                      label: Text(column),
                      backgroundColor: AppColors.warningLight,
                      labelStyle: AppTextStyles.labelMedium.copyWith(
                        color: AppColors.warning,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _NextActionsCard extends StatelessWidget {
  const _NextActionsCard({
    required this.result,
    this.chain,
    this.continuationContext,
  });

  final AnalysisResult result;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final schema = _ResultSchemaMix.fromResult(result);
    final qualityScore = result.qualityAnalysis?.qualityScore;
    final highCorrelationCount =
        result.correlations?.highCorrelations?.length ??
        result.correlations?.correlations?.length ??
        0;
    final nonNormalCount =
        result.statisticalTests?.summary?.nonNormalDistributionCount ?? 0;
    final actions = _collectRecommendations(result);

    final trainingReady = schema.numericCount > 0 && (qualityScore ?? 0) >= 70;
    final featureSelectionNeeded = highCorrelationCount > 0;
    final transformationNeeded = nonNormalCount > 0;

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ConsoleCardHeader(
            title: 'Next Actions',
            subtitle: '把结果转换成后续治理、训练和知识库动作建议。',
            accent: AppColors.cta,
            icon: Icons.alt_route_rounded,
            chain: chain,
            continuationContext: continuationContext,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _ActionBadge(
                label: trainingReady ? '可进入训练' : '训练前需治理',
                tone: trainingReady ? _ActionTone.success : _ActionTone.warning,
              ),
              _ActionBadge(
                label: featureSelectionNeeded ? '建议做特征筛选' : '相关性可控',
                tone: featureSelectionNeeded
                    ? _ActionTone.warning
                    : _ActionTone.info,
              ),
              _ActionBadge(
                label: transformationNeeded ? '建议做分布变换' : '分布基本稳定',
                tone: transformationNeeded
                    ? _ActionTone.cta
                    : _ActionTone.success,
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (actions.isEmpty)
            Text(
              '当前没有额外建议，可继续查看详细面板并决定是否送入 AI Lab。',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            )
          else
            Column(
              children: actions
                  .map(
                    (action) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            margin: const EdgeInsets.only(top: 6),
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: AppColors.cta,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              action,
                              style: AppTextStyles.bodySmall.copyWith(
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
        ],
      ),
    );
  }
}

class _PreviewCard extends StatelessWidget {
  const _PreviewCard({required this.preview, required this.columns});

  final List<Map<String, dynamic>> preview;
  final List<String> columns;

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('数据预览', style: AppTextStyles.h4),
          const SizedBox(height: 4),
          Text(
            '预览前 ${preview.length} 行，用于快速检查字段顺序、空值和样例数据。',
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 14),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              key: const ValueKey('analysis-preview-table'),
              headingRowColor: WidgetStatePropertyAll(AppColors.surfaceVariant),
              columns: columns
                  .map(
                    (column) => DataColumn(
                      label: Text(
                        column,
                        style: AppTextStyles.labelMedium.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  )
                  .toList(),
              rows: preview
                  .map(
                    (row) => DataRow(
                      cells: columns
                          .map(
                            (column) => DataCell(
                              Text(
                                row[column]?.toString() ?? '',
                                style: AppTextStyles.bodySmall,
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }
}

class _ConsoleCardHeader extends StatelessWidget {
  const _ConsoleCardHeader({
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.icon,
    this.chain,
    this.continuationContext,
  });

  final String title;
  final String subtitle;
  final Color accent;
  final IconData icon;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    return IncidentCardHeader(
      accent: accent,
      icon: icon,
      title: title,
      subtitle: subtitle,
      workspaceLabel:
          continuationContext?.workspaceTargetLabel ??
          chain?.workspaceTargetLabel,
      cardLabel: continuationContext?.cardTargetLabel ?? chain?.cardTargetLabel,
      incidentLabel:
          continuationContext?.incidentTargetLabel ??
          chain?.incidentTargetLabel,
      summary: continuationContext?.workspaceBrief ?? chain?.workspaceBrief,
    );
  }
}

class _AnalysisInfoRow extends StatelessWidget {
  const _AnalysisInfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: AppTextStyles.labelMedium),
            Text(value, style: AppTextStyles.labelLarge),
          ],
        ),
      ),
    );
  }
}

enum _ActionTone { success, warning, info, cta }

class _ActionBadge extends StatelessWidget {
  const _ActionBadge({required this.label, required this.tone});

  final String label;
  final _ActionTone tone;

  @override
  Widget build(BuildContext context) {
    final colors = switch (tone) {
      _ActionTone.success => (AppColors.success, AppColors.successLight),
      _ActionTone.warning => (AppColors.warning, AppColors.warningLight),
      _ActionTone.info => (AppColors.primary, AppColors.infoLight),
      _ActionTone.cta => (AppColors.cta, const Color(0xFFFFEDD5)),
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

String _assetConsoleFocusArea(AssetChainSummary? chain) {
  switch (chain?.cardTarget) {
    case 'schema_topology':
      return 'schema';
    case 'field_distribution':
      return 'distribution';
    case 'risk_digest':
      return 'risk';
    case 'next_actions':
      return 'actions';
    case 'dataset_current_asset':
    case 'dataset_reference_asset':
      return 'schema';
    case 'dataset_drift_report':
    case 'dataset_governance_decision':
      return 'risk';
    case 'dataset_results':
      return 'actions';
    case 'dataset_job_panel':
      return 'distribution';
  }
  switch (chain?.sectionTarget) {
    case 'data_analysis_operations':
      return 'distribution';
    case 'data_analysis_results':
      return 'schema';
  }
  if (chain?.status == 'watch' || chain?.status == 'incident') {
    return 'risk';
  }
  if (chain?.status == 'action') {
    return 'actions';
  }
  return 'schema';
}

Widget _consoleShell({
  required bool highlighted,
  required Color color,
  required Widget child,
}) {
  if (!highlighted) {
    return child;
  }
  return Container(
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
      border: Border.all(color: color.withValues(alpha: 0.32), width: 1.3),
    ),
    child: child,
  );
}

class _DistributionBar extends StatelessWidget {
  const _DistributionBar({
    required this.label,
    required this.ratio,
    required this.value,
    required this.color,
    required this.background,
  });

  final String label;
  final double ratio;
  final String value;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    final clampedRatio = ratio.clamp(0.0, 1.0);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: AppTextStyles.labelMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
              Text(
                '$value · ${(clampedRatio * 100).toStringAsFixed(0)}%',
                style: AppTextStyles.labelLarge.copyWith(color: color),
              ),
            ],
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: clampedRatio,
            minHeight: 8,
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            backgroundColor: Colors.white,
            color: color,
          ),
        ],
      ),
    );
  }
}

class _AnalysisSummaryItem extends StatelessWidget {
  const _AnalysisSummaryItem({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    required this.background,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 170),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(height: 10),
          Text(label, style: AppTextStyles.labelMedium.copyWith(color: color)),
          const SizedBox(height: 4),
          Text(value, style: AppTextStyles.h4),
        ],
      ),
    );
  }
}

class _ResultSchemaMix {
  const _ResultSchemaMix({
    required this.numericCount,
    required this.categoricalCount,
    required this.datetimeCount,
  });

  final int numericCount;
  final int categoricalCount;
  final int datetimeCount;

  factory _ResultSchemaMix.fromResult(AnalysisResult result) {
    var numeric = 0;
    var categorical = 0;
    var datetime = 0;

    for (final type in result.basicInfo.columnTypes.values) {
      final normalized = type.toLowerCase();
      if (_isNumeric(normalized)) {
        numeric += 1;
      } else if (_isDatetime(normalized)) {
        datetime += 1;
      } else {
        categorical += 1;
      }
    }

    return _ResultSchemaMix(
      numericCount: numeric,
      categoricalCount: categorical,
      datetimeCount: datetime,
    );
  }
}

bool _isNumeric(String value) {
  return value.contains('int') ||
      value.contains('float') ||
      value.contains('double') ||
      value.contains('decimal') ||
      value.contains('number');
}

bool _isDatetime(String value) {
  return value.contains('date') ||
      value.contains('time') ||
      value.contains('timestamp');
}

String _formatResultPercentage(double value) {
  final normalized = value <= 1 ? value * 100 : value;
  return '${normalized.toStringAsFixed(normalized >= 10 ? 1 : 2)}%';
}

String _dominantSchemaLabel(_ResultSchemaMix mix) {
  if (mix.numericCount >= mix.categoricalCount &&
      mix.numericCount >= mix.datetimeCount) {
    return '数值主导';
  }
  if (mix.categoricalCount >= mix.datetimeCount) {
    return '类别主导';
  }
  return '时间主导';
}

String _trainingPosture(_ResultSchemaMix mix) {
  if (mix.numericCount == 0) {
    return '建模信号偏弱';
  }
  if (mix.numericCount >= mix.categoricalCount) {
    return '适合继续做监督训练';
  }
  return '训练前建议补编码/特征工程';
}

String _ragPosture(_ResultSchemaMix mix) {
  if (mix.categoricalCount + mix.datetimeCount == 0) {
    return '索引价值一般';
  }
  if (mix.categoricalCount >= mix.numericCount) {
    return '适合形成知识索引';
  }
  return '适合作为结构化知识补充';
}

List<String> _collectRecommendations(AnalysisResult result) {
  final items = <String>[];

  void addAll(List<String>? values) {
    if (values == null) {
      return;
    }
    for (final value in values) {
      final normalized = value.trim();
      if (normalized.isNotEmpty && !items.contains(normalized)) {
        items.add(normalized);
      }
      if (items.length >= 4) {
        return;
      }
    }
  }

  addAll(result.qualityAnalysis?.recommendations);
  addAll(result.correlations?.suggestions);
  addAll(result.statisticalTests?.suggestions);
  return items.take(4).toList(growable: false);
}

IconData _columnTypeIcon(String? type) {
  final normalizedType = (type ?? '').toLowerCase();
  if (normalizedType.contains('int') || normalizedType.contains('float')) {
    return Icons.numbers;
  }
  if (normalizedType.contains('object') || normalizedType.contains('string')) {
    return Icons.text_fields;
  }
  if (normalizedType.contains('datetime')) {
    return Icons.calendar_today;
  }
  if (normalizedType.contains('bool')) {
    return Icons.toggle_on;
  }
  return Icons.help_outline;
}

Color _columnTypeColor(String? type) {
  final normalizedType = (type ?? '').toLowerCase();
  if (normalizedType.contains('int') || normalizedType.contains('float')) {
    return AppColors.infoLight;
  }
  if (normalizedType.contains('object') || normalizedType.contains('string')) {
    return AppColors.successLight;
  }
  if (normalizedType.contains('datetime')) {
    return const Color(0xFFF3E8FF);
  }
  if (normalizedType.contains('bool')) {
    return AppColors.warningLight;
  }
  return AppColors.surfaceVariant;
}
