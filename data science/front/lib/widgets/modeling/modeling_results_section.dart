/// 建模页面结果展示组件
library;

import 'package:flutter/material.dart';

import '../../models/dashboard_summary.dart';
import '../../models/optimization_result.dart';
import '../../models/workbench_launch_context.dart';
import '../analysis/feature_importance_chart.dart';
import '../operations/asset_chain_section_header.dart';
import '../power_chart_widget.dart';
import '../soc_chart_widget.dart';
import 'modeling_health_section.dart';
import 'modeling_state_cards.dart';
import 'optimization_insights_section.dart';

class ModelingResultsSection extends StatelessWidget {
  const ModelingResultsSection({
    super.key,
    required this.isLoading,
    required this.errorMessage,
    required this.result,
    required this.previousResult,
    required this.onDismissError,
    this.chain,
    this.continuationContext,
  });

  final bool isLoading;
  final String? errorMessage;
  final OptimizationResponse? result;
  final OptimizationResponse? previousResult;
  final VoidCallback onDismissError;
  final AssetChainSummary? chain;
  final WorkbenchLaunchContext? continuationContext;

  @override
  Widget build(BuildContext context) {
    final optimization = result?.optimization;
    final modelExplainability = result?.modelExplainability;
    final modelInfo = result?.modelInfo;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (result != null || isLoading || errorMessage != null) ...[
          AssetChainSectionHeader(
            title: '结果控制台',
            subtitle: '把模型健康、优化结果、图表和解释性集中到同一结果层，延续当前工作台上下文。',
            chain: chain,
            continuationContext: continuationContext,
            icon: Icons.auto_graph_rounded,
          ),
          const SizedBox(height: 16),
        ],
        if (errorMessage != null)
          ModelingErrorCard(message: errorMessage!, onDismiss: onDismissError),
        if (isLoading) ...[
          if (errorMessage != null) const SizedBox(height: 16),
          const ModelingLoadingCard(),
        ],
        if (modelInfo != null) ...[
          if (errorMessage != null || isLoading) const SizedBox(height: 16),
          ModelingHealthCard(modelInfo: modelInfo),
        ],
        if (optimization != null) ...[
          if (errorMessage != null || isLoading || modelInfo != null)
            const SizedBox(height: 16),
          OptimizationMetricsSection(
            optimization: optimization,
            previousResult: previousResult,
          ),
          if (optimization.diagnostics != null ||
              optimization.constraintHits != null) ...[
            const SizedBox(height: 12),
            SolverDiagnosticsCard(optimization: optimization),
          ],
          const SizedBox(height: 24),
          PowerChartWidget(chartData: optimization.chartData),
          const SizedBox(height: 16),
          SocChartWidget(chartData: optimization.chartData),
          const SizedBox(height: 16),
          OptimizationStrategyDetailsCard(optimization: optimization),
          if (modelExplainability != null) ...[
            const SizedBox(height: 16),
            _ExplainabilityExpansionCard(
              modelExplainability: modelExplainability,
            ),
          ],
        ],
        if (result == null && !isLoading && errorMessage == null)
          const ModelingEmptyStateCard(),
      ],
    );
  }
}

class _ExplainabilityExpansionCard extends StatefulWidget {
  const _ExplainabilityExpansionCard({required this.modelExplainability});

  final ModelExplainability modelExplainability;

  @override
  State<_ExplainabilityExpansionCard> createState() =>
      _ExplainabilityExpansionCardState();
}

class _ExplainabilityExpansionCardState
    extends State<_ExplainabilityExpansionCard> {
  static const _storageKey = 'model-explainability-expansion';
  bool _isExpanded = true;
  bool _didRestoreState = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_didRestoreState) {
      return;
    }
    final restored =
        PageStorage.maybeOf(
              context,
            )?.readState(context, identifier: _storageKey)
            as bool?;
    if (restored != null) {
      _isExpanded = restored;
    }
    _didRestoreState = true;
  }

  void _handleExpansionChanged(bool value) {
    setState(() {
      _isExpanded = value;
    });
    PageStorage.maybeOf(
      context,
    )?.writeState(context, value, identifier: _storageKey);
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      key: const PageStorageKey<String>(_storageKey),
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            key: const ValueKey('model-explainability-header'),
            color: Colors.grey[200],
            padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
            child: Row(
              children: [
                Icon(Icons.psychology, color: Colors.purple[600]),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'AI 预测解释',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '了解哪些因素影响了负载预测',
                        style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  key: const ValueKey('model-explainability-toggle'),
                  tooltip: _isExpanded ? '收起 AI 预测解释' : '展开 AI 预测解释',
                  onPressed: () => _handleExpansionChanged(!_isExpanded),
                  icon: AnimatedRotation(
                    turns: _isExpanded ? 0 : 0.5,
                    duration: const Duration(milliseconds: 180),
                    curve: Curves.easeOut,
                    child: const Icon(Icons.keyboard_arrow_up_rounded),
                  ),
                ),
              ],
            ),
          ),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 180),
            switchInCurve: Curves.easeOut,
            switchOutCurve: Curves.easeIn,
            child: _isExpanded
                ? Padding(
                    key: const ValueKey('model-explainability-body'),
                    padding: const EdgeInsets.all(16),
                    child: FeatureImportanceChart(
                      key: const PageStorageKey<String>(
                        'feature-importance-chart',
                      ),
                      featureImportance:
                          widget.modelExplainability.featureImportance,
                      featureDescriptions:
                          widget.modelExplainability.featureDescriptions,
                      interpretation: widget.modelExplainability.interpretation,
                    ),
                  )
                : const SizedBox.shrink(
                    key: ValueKey('model-explainability-collapsed-body'),
                  ),
          ),
        ],
      ),
    );
  }
}
