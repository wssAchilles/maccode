import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/ai_lab_launch_intent.dart';
import 'package:front/models/dashboard_summary.dart';
import 'package:front/models/data_analysis_launch_intent.dart';
import 'package:front/models/optimization_launch_intent.dart';
import 'package:front/repositories/dashboard_repository.dart';
import 'package:front/screens/operations_hub_screen.dart';
import 'package:front/widgets/operations/duty_context_board.dart';
import 'package:front/viewmodels/dashboard_view_model.dart';
import 'package:front/widgets/operations/workbench_page_frame.dart';

class _FakeDashboardRepository implements DashboardRepository {
  const _FakeDashboardRepository(this.summary);

  final DashboardSummary summary;

  @override
  Future<DashboardSummary> getSummary() async => summary;
}

DashboardSummary _buildSummary({List<Map<String, Object?>> overviewActions = const []}) {
  return DashboardSummary.fromJson({
    'system_status': [
      {
        'key': 'api',
        'label': 'API',
        'status': 'healthy',
        'message': 'ok',
      },
    ],
    'kpis': {
      'dataset_count': 1,
      'analysis_count': 1,
      'model_count': 1,
      'jobs_24h': 1,
      'failed_jobs': 0,
    },
    'duty_summary': {
      'focus_chain_key': 'model',
      'focus_chain_label': '模型资产',
      'focus_workspace_target': 'ai_runtime',
      'focus_workspace_target_label': 'AI 运行控制区',
      'focus_card_target': 'runtime_product',
      'focus_card_target_label': '运行产物',
      'focus_incident_target': 'runtime',
      'focus_incident_target_label': '活跃作业',
      'focus_watch': '优先处理模型训练链路',
      'overview_actions': overviewActions,
      'audit_actions': const [],
    },
    'recent_jobs': const [],
    'recent_assets': const [],
    'recent_history': const [],
    'alerts': const [],
    'asset_summary': {
      'inventory': {
        'dataset_assets': 1,
        'model_assets': 1,
        'knowledge_assets': 0,
        'optimization_assets': 0,
      },
      'datasets': const [],
      'models': const [],
      'knowledge_bases': const [],
      'optimizations': const [],
      'failure_chains': const [],
      'governance': const [],
      'chain_summaries': [
        {
          'key': 'dataset',
          'label': '数据资产',
          'status': 'healthy',
          'status_label': '链路健康',
          'priority_score': 60,
          'owner_label': 'DataOps',
          'sla_minutes': 30,
          'escalation_label': 'P2',
          'elapsed_minutes': 5,
          'overdue_minutes': 0,
          'is_overdue': false,
          'escalation_tier': 1,
          'escalation_state_label': '观察中',
          'latest_version': 'v1',
          'latest_label': 'latest',
          'lineage_summary': 'dataset lineage',
          'failure_summary': '--',
          'focus_label': '当前资产',
          'focus_detail': '上传并分析数据',
          'focus_target': 'dataset_current_asset',
          'focus_target_label': '当前资产',
          'section_target': 'data_analysis_operations',
          'section_target_label': '运营态工作台',
          'workspace_target': 'data_governance',
          'workspace_target_label': '资产治理板',
          'workspace_brief': '数据分析工作台 · 上传数据并查看治理和结果。',
          'card_target': 'strategy',
          'card_target_label': '执行策略',
          'incident_target': 'asset',
          'incident_target_label': '资产状态',
          'incident_brief': '数据资产状态正常',
          'narrative_target': 'target',
          'narrative_target_label': '目标落点',
          'disposition_target': 'focus',
          'disposition_target_label': '当前焦点',
          'runbook_title': '数据资产 Runbook',
          'runbook_steps': const ['检查数据'],
          'activity_title': '最近分析',
          'activity_status': 'idle',
          'activity_source': 'dashboard',
          'failure_phase': '--',
          'failure_source': '--',
          'job_status': '--',
          'job_progress': 0,
          'job_phase': '--',
          'action_label': '打开数据分析',
          'timeline': const [],
        },
        {
          'key': 'model',
          'label': '模型资产',
          'status': 'warning',
          'status_label': '需要关注',
          'priority_score': 90,
          'owner_label': 'MLOps',
          'sla_minutes': 15,
          'escalation_label': 'P1',
          'elapsed_minutes': 8,
          'overdue_minutes': 0,
          'is_overdue': false,
          'escalation_tier': 2,
          'escalation_state_label': '待处理',
          'latest_version': 'v2',
          'latest_label': 'latest',
          'lineage_summary': 'model lineage',
          'failure_summary': '--',
          'focus_label': '运行产物',
          'focus_detail': '开始模型训练',
          'focus_target': 'model_runtime',
          'focus_target_label': '训练运行态',
          'section_target': 'ai_lab_runtime',
          'section_target_label': '运行控制区',
          'workspace_target': 'ai_runtime',
          'workspace_target_label': 'AI 运行控制区',
          'workspace_brief': 'AI Lab 训练车道 · 提交训练任务并跟进队列、产物与模型资产。',
          'card_target': 'runtime_product',
          'card_target_label': '运行产物',
          'incident_target': 'runtime',
          'incident_target_label': '活跃作业',
          'incident_brief': '训练链路待处理',
          'narrative_target': 'job',
          'narrative_target_label': '活跃作业',
          'disposition_target': 'job',
          'disposition_target_label': '活跃作业',
          'runbook_title': '模型训练 Runbook',
          'runbook_steps': const ['提交训练'],
          'activity_title': '最近训练',
          'activity_status': 'idle',
          'activity_source': 'dashboard',
          'failure_phase': '--',
          'failure_source': '--',
          'job_status': '--',
          'job_progress': 0,
          'job_phase': '--',
          'action_label': '打开 AI Lab',
          'timeline': const [],
        },
      ],
    },
  });
}

Widget _buildHarness({
  required DashboardSummary summary,
  ValueChanged<int>? onNavigateToTab,
  ValueChanged<AiLabLaunchIntent>? onOpenAiLab,
  ValueChanged<DataAnalysisLaunchIntent>? onOpenDataAnalysis,
  ValueChanged<OptimizationLaunchIntent>? onOpenOptimization,
}) {
  final viewModel = DashboardViewModel(
    repository: _FakeDashboardRepository(summary),
  );
  return MaterialApp(
    home: OperationsHubScreen(
      viewModel: viewModel,
      onNavigateToTab: onNavigateToTab ?? (_) {},
      onOpenAiLab: onOpenAiLab,
      onOpenDataAnalysis: onOpenDataAnalysis,
      onOpenOptimization: onOpenOptimization,
      surfaceMode: WorkbenchSurfaceMode.embedded,
    ),
  );
}

void main() {
  testWidgets('OperationsHubScreen dispatches overview model action to AI Lab', (
    WidgetTester tester,
  ) async {
    AiLabLaunchIntent? receivedIntent;
    final summary = _buildSummary(
      overviewActions: const [
        {
          'command': 'open_workspace',
          'label': '开始模型训练',
          'tone': 'primary',
          'chain_key': 'model',
          'chain_label': '模型资产',
          'workspace_target': 'ai_runtime',
          'workspace_target_label': 'AI 运行控制区',
          'card_target': 'runtime_product',
          'card_target_label': '运行产物',
          'incident_target': 'runtime',
          'incident_target_label': '活跃作业',
          'workspace_brief': 'AI Lab 训练车道 · 提交训练任务并跟进队列、产物与模型资产。',
        },
      ],
    );

    await tester.pumpWidget(
      _buildHarness(
        summary: summary,
        onOpenAiLab: (intent) => receivedIntent = intent,
      ),
    );
    await tester.pumpAndSettle();

    final actionFinder = find.descendant(
      of: find.byType(DutyContextBoard),
      matching: find.widgetWithText(FilledButton, '开始模型训练'),
    );
    expect(actionFinder, findsOneWidget);
    final button = tester.widget<FilledButton>(actionFinder);
    button.onPressed!.call();
    await tester.pumpAndSettle();

    expect(receivedIntent, isNotNull);
    expect(receivedIntent!.target, AiLabLaunchTarget.deepLearning);
    expect(receivedIntent!.context?.workspaceTargetLabel, 'AI 运行控制区');
    expect(receivedIntent!.context?.cardTargetLabel, '运行产物');
    expect(receivedIntent!.sourceLabel, contains('Duty Actions'));
  });

  testWidgets('OperationsHubScreen dispatches audit overview action to tab 4', (
    WidgetTester tester,
  ) async {
    int? targetTab;
    final summary = _buildSummary(
      overviewActions: const [
        {
          'command': 'open_audit',
          'label': '查看历史与审计',
          'tone': 'outline',
          'chain_key': '',
          'chain_label': '历史与审计',
          'workspace_target': 'audit_center',
          'workspace_target_label': '历史与审计',
          'card_target': 'summary',
          'card_target_label': '当前卡片',
          'incident_target': 'focus',
          'incident_target_label': '当前焦点',
          'workspace_brief': '查看历史、审计流和资产回放。',
        },
      ],
    );

    await tester.pumpWidget(
      _buildHarness(
        summary: summary,
        onNavigateToTab: (tab) => targetTab = tab,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('查看历史与审计'));
    await tester.pumpAndSettle();

    expect(targetTab, 4);
  });

  testWidgets('OperationsHubScreen falls back to dataset quick action when overview actions are empty', (
    WidgetTester tester,
  ) async {
    DataAnalysisLaunchIntent? receivedIntent;
    final summary = _buildSummary();

    await tester.pumpWidget(
      _buildHarness(
        summary: summary,
        onOpenDataAnalysis: (intent) => receivedIntent = intent,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('上传并分析数据'));
    await tester.pumpAndSettle();

    expect(receivedIntent, isNotNull);
    expect(receivedIntent!.context?.workspaceTargetLabel, '分析执行区');
    expect(receivedIntent!.context?.cardTargetLabel, '执行策略');
    expect(receivedIntent!.sourceLabel, contains('Duty Actions'));
  });
}
