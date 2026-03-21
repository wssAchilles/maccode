import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/dashboard_summary.dart';
import 'package:front/widgets/operations/asset_governance_queue.dart';
import 'package:front/widgets/operations/incident_runbook_board.dart';
import 'package:front/widgets/operations/incident_priority_strip.dart';
import 'package:front/widgets/operations/operations_event_bus_board.dart';
import 'package:front/widgets/operations/workspace_action_lane.dart';
import 'package:front/widgets/operations/workbench_section_signal.dart';

void main() {
  testWidgets('AssetGovernanceQueue shows sanitized workspace summary', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AssetGovernanceQueue(
            items: const [
              AssetGovernanceItem(
                key: 'dataset',
                label: '数据资产',
                riskLevel: 'warning',
                assetCount: 3,
                failedJobs: 1,
                ownerLabel: '值班人',
                slaMinutes: 30,
                escalationLabel: '仍在 SLA 内',
                latestVersion: 'v2',
                latestLabel: '最新版本',
                lineageSummary: 'dataset -> training',
                failureSummary: '--',
                recommendedAction: '请复核数据资产治理结论',
                actionLabel: '打开工作台',
                workspaceTarget: 'data_governance',
                workspaceTargetLabel: '资产治理板',
                workspaceBrief: 'completed · 100% · 当前卡片',
              ),
            ],
            onAction: _noopGovernance,
          ),
        ),
      ),
    );

    expect(find.text('优先核对当前资产、质量和治理结论。'), findsNWidgets(2));
    expect(find.text('completed · 100% · 当前卡片'), findsNothing);
  });

  testWidgets('IncidentRunbookBoard shows sanitized workspace summary', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: IncidentRunbookBoard(
            summary: AssetSummary(
              inventory: const AssetInventory(
                datasetAssets: 0,
                modelAssets: 0,
                knowledgeAssets: 0,
                optimizationAssets: 0,
              ),
              datasets: const [],
              models: const [],
              knowledgeBases: const [],
              optimizations: const [],
              failureChains: const [],
              governance: const [],
              chainSummaries: [
                _chain(
                  key: 'model',
                  label: '模型资产',
                  workspaceTarget: 'ai_runtime',
                  workspaceTargetLabel: 'AI 运行控制区',
                  cardTarget: 'runtime_product',
                  cardTargetLabel: '运行产物',
                  incidentTarget: 'runtime',
                  incidentTargetLabel: '运行态',
                  sectionTarget: 'ai_lab_runtime',
                  sectionTargetLabel: '运行控制区',
                  workspaceBrief: 'completed · 100% · 运行控制区',
                  incidentBrief: '训练链路待处理',
                ),
              ],
            ),
            onOpenChain: _noopChain,
          ),
        ),
      ),
    );

    expect(find.text('优先跟进训练队列、产物与模型资产。'), findsOneWidget);
    expect(find.text('completed · 100% · 运行控制区'), findsNothing);
  });

  testWidgets('WorkspaceContextBanner hides generic chips and machine summary', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: WorkspaceContextBanner(
            accent: Colors.blue,
            workspaceLabel: 'AI 运行控制区',
            cardLabel: '当前卡片',
            incidentLabel: '值班时限',
            summary: 'completed · 100% · 运行控制区',
          ),
        ),
      ),
    );

    expect(find.text('AI 运行控制区'), findsOneWidget);
    expect(find.text('当前卡片'), findsNothing);
    expect(find.text('Current watch · 值班时限'), findsNothing);
    expect(find.text('completed · 100% · 运行控制区'), findsNothing);
  });

  testWidgets('WorkbenchSectionSignal hides generic chips and machine state', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: WorkbenchSectionSignal(
            chain: _chain(
              key: 'knowledge',
              label: '知识资产',
              workspaceTarget: 'ai_runtime',
              workspaceTargetLabel: 'AI 运行控制区',
              cardTarget: 'summary',
              cardTargetLabel: '当前卡片',
              incidentTarget: 'focus',
              incidentTargetLabel: '值班时限',
              workspaceBrief: 'completed · 100% · 运行控制区',
              incidentBrief: 'completed · 100% · 运行控制区',
            ),
            title: '知识执行面',
            description: '测试摘要清理。',
            icon: Icons.auto_stories_rounded,
          ),
        ),
      ),
    );

    expect(find.text('当前卡片'), findsNothing);
    expect(find.text('值班时限'), findsNothing);
    expect(find.text('completed · 100% · 运行控制区'), findsNothing);
    expect(find.text('AI 运行控制区'), findsWidgets);
    expect(find.text('已完成'), findsOneWidget);
  });

  testWidgets(
    'WorkbenchSectionSignal uses concise watch and execution summary for healthy optimization chains',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: WorkbenchSectionSignal(
              chain: _chain(
                key: 'optimization',
                label: '优化资产',
                workspaceTarget: 'optimization_registry',
                workspaceTargetLabel: '优化注册表',
                cardTarget: 'latest_snapshot',
                cardTargetLabel: '最新快照',
                incidentTarget: 'asset',
                incidentTargetLabel: '资产状态',
                workspaceBrief: 'completed · 100% · 优化注册表',
                incidentBrief: '资产状态 · 优化注册表 · 2026-03-14',
              ),
              title: '后台求解任务',
              description: '测试优化链路摘要清理。',
              icon: Icons.bolt_rounded,
            ),
          ),
        ),
      );

      expect(
        find.text('latest v1 · 最新版本 · 优化注册表'),
        findsNothing,
      );
      expect(
        find.text('资产状态 · 资产状态 · 优化注册表 · 2026-03-14'),
        findsNothing,
      );
      expect(find.text('资产状态 · 优先核对最新快照与结果摘要。'), findsOneWidget);
    },
  );

  testWidgets('IncidentPriorityStrip hides generic chips and machine summary', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: IncidentPriorityStrip(
            summary: AssetSummary(
              inventory: const AssetInventory(
                datasetAssets: 0,
                modelAssets: 0,
                knowledgeAssets: 0,
                optimizationAssets: 0,
              ),
              datasets: const [],
              models: const [],
              knowledgeBases: const [],
              optimizations: const [],
              failureChains: const [],
              governance: const [],
              chainSummaries: [
                _chain(
                  key: 'model',
                  label: '模型资产',
                  workspaceTarget: 'ai_runtime',
                  workspaceTargetLabel: 'AI 运行控制区',
                  cardTarget: 'summary',
                  cardTargetLabel: '当前卡片',
                  incidentTarget: 'focus',
                  incidentTargetLabel: '值班时限',
                  workspaceBrief: 'completed · 100% · 当前卡片',
                  incidentBrief: 'SLA 已超时 · due 03-14 08:20 · 升级到 ML 负责人',
                ),
              ],
            ),
            onOpenChain: _noopChain,
          ),
        ),
      ),
    );

    expect(find.text('当前卡片'), findsNothing);
    expect(find.text('值班时限'), findsNothing);
    expect(find.text('completed · 100% · 当前卡片'), findsNothing);
    expect(find.text('AI 运行控制区'), findsWidgets);
    expect(find.text('优先跟进训练队列、产物与模型资产。'), findsOneWidget);
  });

  testWidgets('OperationsEventBusBoard hides generic chips and machine summary', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: OperationsEventBusBoard(
              summary: DashboardSummary(
                systemStatus: const [],
                kpis: const DashboardKpis(
                  datasetCount: 0,
                  analysisCount: 0,
                  modelCount: 0,
                  jobs24h: 0,
                  failedJobs: 0,
                ),
                recentJobs: const [],
                recentAssets: const [],
                recentHistory: const [],
                alerts: const [],
                assetSummary: AssetSummary(
                  inventory: const AssetInventory(
                    datasetAssets: 0,
                    modelAssets: 0,
                    knowledgeAssets: 0,
                    optimizationAssets: 0,
                  ),
                  datasets: const [],
                  models: const [],
                  knowledgeBases: const [],
                  optimizations: const [],
                  failureChains: const [],
                  governance: const [],
                  chainSummaries: [
                    _chain(
                      key: 'model',
                      label: '模型资产',
                      workspaceTarget: 'ai_runtime',
                      workspaceTargetLabel: 'AI 运行控制区',
                      cardTarget: 'summary',
                      cardTargetLabel: '当前卡片',
                      incidentTarget: 'focus',
                      incidentTargetLabel: '值班时限',
                      workspaceBrief: 'completed · 100% · 当前卡片',
                      incidentBrief: 'completed · 100% · 运行控制区',
                      timeline: const [
                        AssetChainNode(
                          kind: 'event',
                          title: '训练产物更新',
                          detail: '已同步最近模型资产',
                          level: 'info',
                          badge: 'UPDATE',
                          sourceLabel: 'unit-test',
                          versionTag: 'v1',
                          phaseLabel: 'completed',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              onOpenChain: _noopChain,
            ),
          ),
        ),
      ),
    );

    expect(find.text('当前卡片'), findsNothing);
    expect(find.text('值班时限'), findsNothing);
    expect(find.text('completed · 100% · 当前卡片'), findsNothing);
    expect(find.text('completed · 100% · 运行控制区'), findsNothing);
    expect(find.text('AI 运行控制区'), findsWidgets);
    expect(find.text('优先跟进训练队列、产物与模型资产。'), findsOneWidget);
  });
}

void _noopGovernance(AssetGovernanceItem _) {}

void _noopChain(AssetChainSummary _) {}

AssetChainSummary _chain({
  String key = 'dataset',
  String label = '数据资产',
  String sectionTarget = 'data_analysis_results',
  String sectionTargetLabel = '结果资产台',
  String workspaceTarget = 'data_governance',
  String workspaceTargetLabel = '资产治理板',
  String cardTarget = 'current_asset',
  String cardTargetLabel = '当前资产',
  String incidentTarget = 'asset',
  String incidentTargetLabel = '资产',
  String workspaceBrief = '当前资产已载入工作台',
  String incidentBrief = '资产 · 当前资产已载入工作台',
  List<AssetChainNode> timeline = const [],
}) {
  return AssetChainSummary(
    key: key,
    label: label,
    status: 'healthy',
    statusLabel: '正常',
    priorityScore: 10,
    ownerLabel: '值班人',
    slaMinutes: 30,
    escalationLabel: '仍在 SLA 内',
    elapsedMinutes: 5,
    overdueMinutes: 0,
    isOverdue: false,
    escalationTier: 0,
    escalationStateLabel: '正常',
    latestVersion: 'v1',
    latestLabel: '最新版本',
    lineageSummary: 'lineage',
    failureSummary: 'none',
    focusLabel: '资产',
    focusDetail: '',
    focusTarget: cardTarget,
    focusTargetLabel: cardTargetLabel,
    sectionTarget: sectionTarget,
    sectionTargetLabel: sectionTargetLabel,
    workspaceTarget: workspaceTarget,
    workspaceTargetLabel: workspaceTargetLabel,
    workspaceBrief: workspaceBrief,
    cardTarget: cardTarget,
    cardTargetLabel: cardTargetLabel,
    incidentTarget: incidentTarget,
    incidentTargetLabel: incidentTargetLabel,
    incidentBrief: incidentBrief,
    narrativeTarget: 'target',
    narrativeTargetLabel: '当前卡片',
    dispositionTarget: 'focus',
    dispositionTargetLabel: '当前卡片',
    runbookTitle: '模型训练处置',
    runbookSteps: const ['检查训练队列'],
    activityTitle: 'activity',
    activityStatus: 'active',
    activitySource: 'unit-test',
    failurePhase: 'none',
    failureSource: 'none',
    jobStatus: 'succeeded',
    jobProgress: 100,
    jobPhase: 'completed',
    actionLabel: '打开工作台',
    timeline: timeline,
  );
}
