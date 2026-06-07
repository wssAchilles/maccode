import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/dashboard_summary.dart';
import 'package:front/repositories/dashboard_repository.dart';
import 'package:front/screens/operations_hub_screen.dart';
import 'package:front/viewmodels/dashboard_view_model.dart';
import 'package:front/widgets/operations/workbench_page_frame.dart';

class _FakeDashboardRepository implements DashboardRepository {
  const _FakeDashboardRepository(this.summary);

  final DashboardSummary summary;

  @override
  Future<DashboardSummary> getSummary() async => summary;
}

DashboardSummary _buildSummary({
  List<Map<String, Object?>> overviewActions = const [],
  String modelCardTargetLabel = '运行产物',
  String modelIncidentTargetLabel = '活跃作业',
  List<Map<String, Object?>> governance = const [],
  List<Map<String, Object?>> failureChains = const [],
}) {
  return DashboardSummary.fromJson({
    'system_status': [
      {'key': 'api', 'label': 'API', 'status': 'healthy', 'message': 'ok'},
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
      'failure_chains': failureChains,
      'governance': governance,
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
          'card_target_label': modelCardTargetLabel,
          'incident_target': 'runtime',
          'incident_target_label': modelIncidentTargetLabel,
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
        {
          'key': 'knowledge',
          'label': '知识快照',
          'status': 'incident',
          'status_label': '故障待处置',
          'priority_score': 80,
          'owner_label': 'AI 知识平台主管',
          'sla_minutes': 15,
          'escalation_label': '升级到 AI 知识平台主管',
          'elapsed_minutes': 12,
          'overdue_minutes': 3,
          'is_overdue': true,
          'escalation_tier': 2,
          'escalation_state_label': 'SLA 已超时',
          'latest_version': 'v0314-0702',
          'latest_label': '20251209_130622_AEP_hourly',
          'lineage_summary': 'uploads/demo.csv -> ops-knowledge',
          'failure_summary': '--',
          'focus_label': '知识快照',
          'focus_detail': '回填知识入口',
          'focus_target': 'knowledge_runtime',
          'focus_target_label': '知识运行态',
          'section_target': 'ai_lab_runtime',
          'section_target_label': '运行控制区',
          'workspace_target': 'ai_runtime',
          'workspace_target_label': 'AI 运行控制区',
          'workspace_brief': 'AI Lab 知识车道 · 提交构建任务并跟进知识快照、问答治理。',
          'card_target': 'runtime_product',
          'card_target_label': '运行产物',
          'incident_target': 'runtime',
          'incident_target_label': '运行态',
          'incident_brief': '优先核对集合配置和最新知识快照。',
          'narrative_target': 'job',
          'narrative_target_label': '活跃作业',
          'disposition_target': 'job',
          'disposition_target_label': '活跃作业',
          'runbook_title': '知识库构建 Runbook',
          'runbook_steps': const ['回填知识入口'],
          'activity_title': '最近知识库任务',
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

Widget _buildHarness({required DashboardSummary summary}) {
  final viewModel = DashboardViewModel(
    repository: _FakeDashboardRepository(summary),
  )..hydrateSummary(summary);
  return MaterialApp(
    home: OperationsHubScreen(
      viewModel: viewModel,
      onNavigateToTab: (_) {},
      surfaceMode: WorkbenchSurfaceMode.embedded,
    ),
  );
}

void main() {
  testWidgets('OperationsHubScreen renders embedded workbench content', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(_buildHarness(summary: _buildSummary()));
    await tester.pumpAndSettle();

    expect(find.byType(OperationsHubScreen), findsOneWidget);
    expect(find.byType(AppBar), findsNothing);
    expect(find.byType(CustomScrollView), findsOneWidget);
    expect(find.text('Operations Hub'), findsNothing);
  });

  testWidgets('OperationsHubScreen keeps summary-driven decision header', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(_buildHarness(summary: _buildSummary()));
    await tester.pumpAndSettle();

    expect(find.text('今日运营概览'), findsOneWidget);
    expect(find.text('先看状态、锁定风险，再进入唯一需要处理的工作台。'), findsOneWidget);
  });
}
