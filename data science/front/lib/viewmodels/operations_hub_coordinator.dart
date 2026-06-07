library;

import '../models/ai_lab_launch_intent.dart';
import '../models/dashboard_summary.dart';
import '../models/data_analysis_launch_intent.dart';
import '../models/optimization_launch_intent.dart';
import '../utils/asset_chain_context.dart';

class OperationsHubCoordinator {
  const OperationsHubCoordinator({
    required void Function(int tabIndex) navigateToTab,
    void Function(AiLabLaunchIntent intent)? openAiLab,
    void Function(DataAnalysisLaunchIntent intent)? openDataAnalysis,
    void Function(OptimizationLaunchIntent intent)? openOptimization,
  }) : _navigateToTab = navigateToTab,
       _openAiLab = openAiLab,
       _openDataAnalysis = openDataAnalysis,
       _openOptimization = openOptimization;

  final void Function(int tabIndex) _navigateToTab;
  final void Function(AiLabLaunchIntent intent)? _openAiLab;
  final void Function(DataAnalysisLaunchIntent intent)? _openDataAnalysis;
  final void Function(OptimizationLaunchIntent intent)? _openOptimization;

  void openChainWorkspace(AssetChainSummary chain, {required String source}) {
    final context = buildLaunchContextFromChain(chain, prefix: source);
    final sourceLabel = buildChainSourceLabel(
      chain,
      prefix: source,
      includeWorkspaceBrief: true,
    );
    switch (chain.key) {
      case 'dataset':
        final openDataAnalysis = _openDataAnalysis;
        if (openDataAnalysis != null) {
          openDataAnalysis(
            DataAnalysisLaunchIntent.workspace(
              sourceLabel: sourceLabel,
              context: context,
            ),
          );
        } else {
          _navigateToTab(2);
        }
        break;
      case 'model':
        final openAiLab = _openAiLab;
        if (openAiLab != null) {
          openAiLab(
            AiLabLaunchIntent.deepLearning(
              '',
              sourceLabel: sourceLabel,
              context: context,
            ),
          );
        } else {
          _navigateToTab(3);
        }
        break;
      case 'knowledge':
        final openAiLab = _openAiLab;
        if (openAiLab != null) {
          openAiLab(
            AiLabLaunchIntent.rag(
              '',
              sourceLabel: sourceLabel,
              context: context,
            ),
          );
        } else {
          _navigateToTab(3);
        }
        break;
      case 'optimization':
        final openOptimization = _openOptimization;
        if (openOptimization != null) {
          openOptimization(
            OptimizationLaunchIntent(
              sourceLabel: sourceLabel,
              context: context,
            ),
          );
        } else {
          _navigateToTab(1);
        }
        break;
      default:
        _navigateToTab(0);
    }
  }
}
