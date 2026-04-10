/// 深度学习训练结果可视化面板
library;

import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../config/app_theme.dart';
import '../../models/job_record.dart';
import '../common/glass_card.dart';

class DeepLearningTrainingResultPanel extends StatelessWidget {
  const DeepLearningTrainingResultPanel({super.key, required this.job});

  final JobRecord job;

  @override
  Widget build(BuildContext context) {
    final snapshot = _TrainingVisualSnapshot.fromJob(job);
    if (!snapshot.hasAnyData) {
      return const SizedBox.shrink();
    }

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
                    Text('训练结果可视化', style: AppTextStyles.h4),
                    const SizedBox(height: 6),
                    Text(
                      snapshot.summary,
                      style: AppTextStyles.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              _StatusBadge(
                label: job.status == 'succeeded'
                    ? '结果已收敛'
                    : job.isRunning
                    ? '训练进行中'
                    : '结果快照',
                color: job.status == 'succeeded'
                    ? AppColors.success
                    : job.isRunning
                    ? AppColors.cta
                    : AppColors.primary,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _MetricPill(
                label: '训练轮次',
                value: snapshot.epochsLabel,
                accent: AppColors.primary,
              ),
              _MetricPill(
                label: '训练样本',
                value: snapshot.trainingSamplesLabel,
                accent: AppColors.success,
              ),
              _MetricPill(
                label: '验证样本',
                value: snapshot.validationSamplesLabel,
                accent: AppColors.cta,
              ),
              _MetricPill(
                label: '后端',
                value: job.trainingBackend == 'vertex_custom_training'
                    ? 'Vertex'
                    : 'Legacy',
                accent: job.trainingBackend == 'vertex_custom_training'
                    ? AppColors.primary
                    : AppColors.textSecondary,
              ),
            ],
          ),
          const SizedBox(height: 18),
          LayoutBuilder(
            builder: (context, constraints) {
              final stacked = constraints.maxWidth < 980;
              final lossTile = _VisualTile(
                title: '损失收敛曲线',
                subtitle: snapshot.lossSubtitle,
                child: _SeriesChart(
                  primaryLabel: '训练损失',
                  secondaryLabel: '验证损失',
                  primaryColor: AppColors.primary,
                  secondaryColor: AppColors.cta,
                  primarySeries: snapshot.trainingLossSeries,
                  secondarySeries: snapshot.validationLossSeries,
                  fallbackPrimary: snapshot.trainLoss,
                  fallbackSecondary: snapshot.validationLoss,
                ),
              );
              final maeTile = _VisualTile(
                title: '误差收敛曲线',
                subtitle: snapshot.maeSubtitle,
                child: _SeriesChart(
                  primaryLabel: '训练 MAE',
                  secondaryLabel: '验证 MAE',
                  primaryColor: AppColors.success,
                  secondaryColor: AppColors.cta,
                  primarySeries: snapshot.trainingMaeSeries,
                  secondarySeries: snapshot.validationMaeSeries,
                  fallbackPrimary: snapshot.trainMae,
                  fallbackSecondary: snapshot.validationMae,
                ),
              );
              final heatmapTile = _VisualTile(
                title: '误差热力块',
                subtitle: '用色块直接判断训练集与验证集的误差温度差。',
                child: _MetricHeatmap(snapshot: snapshot),
              );
              final splitTile = _VisualTile(
                title: '样本分布',
                subtitle: '查看训练/验证样本配比，避免只看训练曲线。',
                child: _SampleSplitChart(snapshot: snapshot),
              );

              if (stacked) {
                return Column(
                  children: [
                    lossTile,
                    const SizedBox(height: 14),
                    maeTile,
                    const SizedBox(height: 14),
                    heatmapTile,
                    const SizedBox(height: 14),
                    splitTile,
                  ],
                );
              }

              return Column(
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: lossTile),
                      const SizedBox(width: 14),
                      Expanded(child: maeTile),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: heatmapTile),
                      const SizedBox(width: 14),
                      Expanded(child: splitTile),
                    ],
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _VisualTile extends StatelessWidget {
  const _VisualTile({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTextStyles.labelLarge),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 14),
          SizedBox(height: 232, child: child),
        ],
      ),
    );
  }
}

class _SeriesChart extends StatelessWidget {
  const _SeriesChart({
    required this.primaryLabel,
    required this.secondaryLabel,
    required this.primaryColor,
    required this.secondaryColor,
    required this.primarySeries,
    required this.secondarySeries,
    required this.fallbackPrimary,
    required this.fallbackSecondary,
  });

  final String primaryLabel;
  final String secondaryLabel;
  final Color primaryColor;
  final Color secondaryColor;
  final List<double> primarySeries;
  final List<double> secondarySeries;
  final double? fallbackPrimary;
  final double? fallbackSecondary;

  @override
  Widget build(BuildContext context) {
    final hasLineSeries =
        primarySeries.length > 1 || secondarySeries.length > 1;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: hasLineSeries
              ? LineChart(_buildLineData())
              : _FallbackMetricBars(
                  primaryLabel: primaryLabel,
                  secondaryLabel: secondaryLabel,
                  primaryValue: fallbackPrimary,
                  secondaryValue: fallbackSecondary,
                  primaryColor: primaryColor,
                  secondaryColor: secondaryColor,
                ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 8,
          children: [
            _LegendDot(label: primaryLabel, color: primaryColor),
            _LegendDot(label: secondaryLabel, color: secondaryColor),
          ],
        ),
      ],
    );
  }

  LineChartData _buildLineData() {
    final bars = <LineChartBarData>[];
    final allValues = <double>[...primarySeries, ...secondarySeries];
    final minY = allValues.isEmpty ? 0.0 : allValues.reduce(math.min) * 0.92;
    final maxY = allValues.isEmpty ? 1.0 : allValues.reduce(math.max) * 1.08;

    if (primarySeries.isNotEmpty) {
      bars.add(
        LineChartBarData(
          isCurved: true,
          color: primaryColor,
          barWidth: 3,
          dotData: const FlDotData(show: false),
          belowBarData: BarAreaData(
            show: true,
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                primaryColor.withValues(alpha: 0.22),
                primaryColor.withValues(alpha: 0.02),
              ],
            ),
          ),
          spots: [
            for (var index = 0; index < primarySeries.length; index++)
              FlSpot(index.toDouble() + 1, primarySeries[index]),
          ],
        ),
      );
    }

    if (secondarySeries.isNotEmpty) {
      bars.add(
        LineChartBarData(
          isCurved: true,
          color: secondaryColor,
          dashArray: const [8, 4],
          barWidth: 3,
          dotData: const FlDotData(show: false),
          spots: [
            for (var index = 0; index < secondarySeries.length; index++)
              FlSpot(index.toDouble() + 1, secondarySeries[index]),
          ],
        ),
      );
    }

    final maxPoints = math.max(primarySeries.length, secondarySeries.length);

    return LineChartData(
      minX: 1,
      maxX: math.max(maxPoints.toDouble(), 2),
      minY: minY.isFinite ? minY : 0,
      maxY: maxY.isFinite && maxY > minY ? maxY : minY + 1,
      gridData: FlGridData(
        show: true,
        horizontalInterval: ((maxY - minY) / 4).clamp(1e-6, double.infinity),
        getDrawingHorizontalLine: (_) =>
            FlLine(color: AppColors.border, strokeWidth: 1),
        getDrawingVerticalLine: (_) =>
            FlLine(color: AppColors.borderLight, strokeWidth: 1),
      ),
      borderData: FlBorderData(
        show: true,
        border: Border.all(color: AppColors.border),
      ),
      titlesData: FlTitlesData(
        rightTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 28,
            interval: math.max(1, (maxPoints / 4).ceil()).toDouble(),
            getTitlesWidget: (value, meta) {
              return Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  'E${value.toInt()}',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textMuted,
                    fontSize: 11,
                  ),
                ),
              );
            },
          ),
        ),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 42,
            interval: ((maxY - minY) / 4).clamp(1e-6, double.infinity),
            getTitlesWidget: (value, meta) {
              return Text(
                value.toStringAsFixed(value >= 100 ? 0 : 1),
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textMuted,
                  fontSize: 11,
                ),
              );
            },
          ),
        ),
      ),
      lineBarsData: bars,
    );
  }
}

class _FallbackMetricBars extends StatelessWidget {
  const _FallbackMetricBars({
    required this.primaryLabel,
    required this.secondaryLabel,
    required this.primaryValue,
    required this.secondaryValue,
    required this.primaryColor,
    required this.secondaryColor,
  });

  final String primaryLabel;
  final String secondaryLabel;
  final double? primaryValue;
  final double? secondaryValue;
  final Color primaryColor;
  final Color secondaryColor;

  @override
  Widget build(BuildContext context) {
    final values = [primaryValue ?? 0, secondaryValue ?? 0];
    final maxValue = values.reduce(math.max);
    final safeMax = maxValue <= 0 ? 1.0 : maxValue * 1.15;

    return BarChart(
      BarChartData(
        maxY: safeMax,
        gridData: FlGridData(
          show: true,
          getDrawingHorizontalLine: (_) =>
              FlLine(color: AppColors.border, strokeWidth: 1),
        ),
        borderData: FlBorderData(
          show: true,
          border: Border.all(color: AppColors.border),
        ),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (value, meta) => Text(
                value.toStringAsFixed(value >= 100 ? 0 : 1),
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textMuted,
                  fontSize: 11,
                ),
              ),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) {
                final label = switch (value.toInt()) {
                  0 => 'Train',
                  1 => 'Val',
                  _ => '',
                };
                return Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    label,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        barGroups: [
          BarChartGroupData(
            x: 0,
            barRods: [
              BarChartRodData(
                toY: primaryValue ?? 0,
                width: 24,
                borderRadius: BorderRadius.circular(6),
                gradient: LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [primaryColor, primaryColor.withValues(alpha: 0.6)],
                ),
              ),
            ],
          ),
          BarChartGroupData(
            x: 1,
            barRods: [
              BarChartRodData(
                toY: secondaryValue ?? 0,
                width: 24,
                borderRadius: BorderRadius.circular(6),
                gradient: LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [
                    secondaryColor,
                    secondaryColor.withValues(alpha: 0.6),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MetricHeatmap extends StatelessWidget {
  const _MetricHeatmap({required this.snapshot});

  final _TrainingVisualSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final rows = [
      ('Loss', snapshot.trainLoss, snapshot.validationLoss),
      ('MAE', snapshot.trainMae, snapshot.validationMae),
    ];

    return Column(
      children: [
        Row(
          children: const [
            Expanded(child: SizedBox()),
            Expanded(child: _HeatHeader(label: 'Train')),
            SizedBox(width: 10),
            Expanded(child: _HeatHeader(label: 'Val')),
          ],
        ),
        const SizedBox(height: 10),
        for (var rowIndex = 0; rowIndex < rows.length; rowIndex++) ...[
          _HeatRow(
            label: rows[rowIndex].$1,
            trainValue: rows[rowIndex].$2,
            validationValue: rows[rowIndex].$3,
          ),
          if (rowIndex < rows.length - 1) const SizedBox(height: 10),
        ],
      ],
    );
  }
}

class _HeatHeader extends StatelessWidget {
  const _HeatHeader({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        label,
        style: AppTextStyles.bodySmall.copyWith(
          color: AppColors.textMuted,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _HeatRow extends StatelessWidget {
  const _HeatRow({
    required this.label,
    required this.trainValue,
    required this.validationValue,
  });

  final String label;
  final double? trainValue;
  final double? validationValue;

  @override
  Widget build(BuildContext context) {
    final values = [trainValue, validationValue].whereType<double>().toList();
    final minValue = values.isEmpty ? 0.0 : values.reduce(math.min);
    final maxValue = values.isEmpty ? 1.0 : values.reduce(math.max);

    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ),
        Expanded(
          child: _HeatCell(
            value: trainValue,
            minValue: minValue,
            maxValue: maxValue,
            color: AppColors.primary,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _HeatCell(
            value: validationValue,
            minValue: minValue,
            maxValue: maxValue,
            color: AppColors.cta,
          ),
        ),
      ],
    );
  }
}

class _HeatCell extends StatelessWidget {
  const _HeatCell({
    required this.value,
    required this.minValue,
    required this.maxValue,
    required this.color,
  });

  final double? value;
  final double minValue;
  final double maxValue;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final safeValue = value ?? 0;
    final span = maxValue - minValue;
    final normalized = value == null || span <= 0
        ? 0.5
        : ((safeValue - minValue) / span).clamp(0.0, 1.0);

    return Container(
      height: 76,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16 + (normalized * 0.52)),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
        border: Border.all(color: color.withValues(alpha: 0.22)),
      ),
      child: value == null
          ? Text(
              '--',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textMuted,
              ),
            )
          : Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  value!.toStringAsFixed(value! >= 100 ? 0 : 2),
                  style: AppTextStyles.h4.copyWith(
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Container(
                  width: 48,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.55),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: FractionallySizedBox(
                    alignment: Alignment.centerLeft,
                    widthFactor: normalized.clamp(0.15, 1.0),
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: color,
                        borderRadius: BorderRadius.circular(999),
                      ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

class _SampleSplitChart extends StatelessWidget {
  const _SampleSplitChart({required this.snapshot});

  final _TrainingVisualSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final trainingCount = snapshot.trainingSampleCount ?? 0;
    final validationCount = snapshot.validationSampleCount ?? 0;
    final total = math.max(trainingCount + validationCount, 1);
    final trainRatio = trainingCount / total;
    final validationRatio = validationCount / total;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppDecorations.radiusLg),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('训练 / 验证占比', style: AppTextStyles.labelLarge),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
            child: SizedBox(
              height: 22,
              child: Row(
                children: [
                  Expanded(
                    flex: math.max((trainRatio * 100).round(), 1),
                    child: DecoratedBox(
                      decoration: const BoxDecoration(
                        gradient: AppColors.primaryGradient,
                      ),
                    ),
                  ),
                  Expanded(
                    flex: math.max((validationRatio * 100).round(), 1),
                    child: DecoratedBox(
                      decoration: const BoxDecoration(
                        gradient: AppColors.ctaGradient,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          _SplitLegend(
            label: '训练样本',
            value: trainingCount.toString(),
            ratio: trainRatio,
            color: AppColors.primary,
          ),
          const SizedBox(height: 8),
          _SplitLegend(
            label: '验证样本',
            value: validationCount.toString(),
            ratio: validationRatio,
            color: AppColors.cta,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _MiniKpi(
                  label: 'Epoch',
                  value: snapshot.epochsLabel,
                  accent: AppColors.success,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _MiniKpi(
                  label: 'Val 比例',
                  value: '${(validationRatio * 100).toStringAsFixed(0)}%',
                  accent: AppColors.cta,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SplitLegend extends StatelessWidget {
  const _SplitLegend({
    required this.label,
    required this.value,
    required this.ratio,
    required this.color,
  });

  final String label;
  final String value;
  final double ratio;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ),
        Text(
          '${(ratio * 100).toStringAsFixed(0)}%',
          style: AppTextStyles.labelMedium.copyWith(color: color),
        ),
        const SizedBox(width: 10),
        Text(value, style: AppTextStyles.labelLarge),
      ],
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({
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
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: RichText(
        text: TextSpan(
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
          children: [
            TextSpan(text: '$label  '),
            TextSpan(
              text: value,
              style: AppTextStyles.labelLarge.copyWith(
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

class _MiniKpi extends StatelessWidget {
  const _MiniKpi({
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
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppDecorations.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 6),
          Text(value, style: AppTextStyles.h4.copyWith(color: accent)),
        ],
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppDecorations.radiusFull),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelMedium.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _TrainingVisualSnapshot {
  const _TrainingVisualSnapshot({
    required this.trainingLossSeries,
    required this.validationLossSeries,
    required this.trainingMaeSeries,
    required this.validationMaeSeries,
    required this.trainLoss,
    required this.validationLoss,
    required this.trainMae,
    required this.validationMae,
    required this.epochsTrained,
    required this.trainingSampleCount,
    required this.validationSampleCount,
  });

  factory _TrainingVisualSnapshot.fromJob(JobRecord job) {
    return _TrainingVisualSnapshot(
      trainingLossSeries: job.trainingLossSeries,
      validationLossSeries: job.validationLossSeries,
      trainingMaeSeries: job.trainingMaeSeries,
      validationMaeSeries: job.validationMaeSeries,
      trainLoss: job.trainLoss,
      validationLoss: job.validationLoss,
      trainMae: job.trainMae,
      validationMae: job.validationMae,
      epochsTrained: job.epochsTrained,
      trainingSampleCount: job.trainingSampleCount,
      validationSampleCount: job.validationSampleCount,
    );
  }

  final List<double> trainingLossSeries;
  final List<double> validationLossSeries;
  final List<double> trainingMaeSeries;
  final List<double> validationMaeSeries;
  final double? trainLoss;
  final double? validationLoss;
  final double? trainMae;
  final double? validationMae;
  final int? epochsTrained;
  final int? trainingSampleCount;
  final int? validationSampleCount;

  bool get hasAnyData =>
      trainingLossSeries.isNotEmpty ||
      validationLossSeries.isNotEmpty ||
      trainingMaeSeries.isNotEmpty ||
      validationMaeSeries.isNotEmpty ||
      trainLoss != null ||
      validationLoss != null ||
      trainMae != null ||
      validationMae != null ||
      trainingSampleCount != null ||
      validationSampleCount != null;

  String get epochsLabel => epochsTrained?.toString() ?? '--';
  String get trainingSamplesLabel => trainingSampleCount?.toString() ?? '--';
  String get validationSamplesLabel =>
      validationSampleCount?.toString() ?? '--';

  String get summary {
    if (trainingLossSeries.length > 1 || trainingMaeSeries.length > 1) {
      return '训练结束后，首屏直接展示收敛曲线、误差温度和样本分布，不再只剩日志文字。';
    }
    return '当前运行没有完整 epoch 曲线时，仍然保留误差热力块和样本分布做视觉反馈。';
  }

  String get lossSubtitle =>
      trainingLossSeries.length > 1 || validationLossSeries.length > 1
      ? '观察 loss 是否持续下降，以及验证集是否开始偏离。'
      : '没有完整曲线时，退化为最终 Train / Val 对比柱。';

  String get maeSubtitle =>
      trainingMaeSeries.length > 1 || validationMaeSeries.length > 1
      ? '用 MAE 判断预测误差是否稳定收敛。'
      : '没有完整曲线时，退化为最终 Train / Val 对比柱。';
}
