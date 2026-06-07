import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/ai_lab_launch_intent.dart';
import 'package:front/models/dashboard_summary.dart';
import 'package:front/models/job_record.dart';
import 'package:front/widgets/history/history_asset_ledger.dart';

void _setDesktopViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1280, 1000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Finder _verticalScrollable() {
  return find
      .byWidgetPredicate(
        (widget) =>
            widget is Scrollable && widget.axisDirection == AxisDirection.down,
      )
      .first;
}

DashboardSummary _buildSummary() {
  return DashboardSummary.fromJson({
    'system_status': const [
      {'key': 'api', 'label': 'API', 'status': 'healthy', 'message': 'ok'},
    ],
    'kpis': const {
      'dataset_count': 1,
      'analysis_count': 1,
      'model_count': 1,
      'jobs_24h': 1,
      'failed_jobs': 0,
    },
    'duty_summary': const {
      'focus_chain_key': 'knowledge',
      'focus_chain_label': '知识快照',
      'focus_workspace_target': 'ai_runtime',
      'focus_workspace_target_label': 'AI 运行控制区',
      'focus_card_target': 'runtime_product',
      'focus_card_target_label': '运行产物',
      'focus_incident_target': 'runtime',
      'focus_incident_target_label': '运行态',
      'focus_watch': '优先核对集合配置和最新知识快照。',
      'focus_owner_label': 'AI 知识平台主管',
      'focus_escalation_state_label': 'SLA 已超时',
      'audit_actions': [
        {
          'command': 'open_workspace',
          'label': '打开 AI Lab',
          'tone': 'primary',
          'chain_key': 'knowledge',
          'chain_label': '知识快照',
          'workspace_target': 'ai_runtime',
          'workspace_target_label': 'AI 运行控制区',
          'card_target': 'runtime_product',
          'card_target_label': '运行产物',
          'incident_target': 'runtime',
          'incident_target_label': '运行态',
          'workspace_brief': 'AI Lab 知识车道 · 提交构建任务并跟进知识快照、问答治理。',
        },
      ],
      'overview_actions': [],
    },
    'recent_jobs': const [],
    'recent_assets': const [],
    'recent_history': const [],
    'alerts': const [],
    'asset_summary': {
      'inventory': const {
        'dataset_assets': 0,
        'model_assets': 0,
        'knowledge_assets': 1,
        'optimization_assets': 0,
      },
      'datasets': const [],
      'models': const [],
      'knowledge_bases': const [],
      'optimizations': const [],
      'failure_chains': const [],
      'governance': const [],
      'chain_summaries': const [
        {
          'key': 'knowledge',
          'label': '知识快照',
          'status': 'incident',
          'status_label': '故障待处置',
          'priority_score': 300,
          'owner_label': 'AI 知识平台主管',
          'sla_minutes': 15,
          'escalation_label': '升级到 AI 知识平台主管',
          'elapsed_minutes': 30,
          'overdue_minutes': 15,
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
          'runbook_steps': ['回填知识入口'],
          'activity_title': '最近知识库任务',
          'activity_status': 'succeeded',
          'activity_source': 'dashboard',
          'failure_phase': '--',
          'failure_source': '--',
          'job_status': 'succeeded',
          'job_progress': 100,
          'job_phase': 'completed',
          'action_label': '打开 AI Lab',
          'timeline': [],
        },
      ],
    },
  });
}

void main() {
  testWidgets('History asset ledger dispatches chain action open AI Lab', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    AiLabLaunchIntent? capturedIntent;
    final summary = _buildSummary();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: HistoryAssetLedger(
              jobs: const [],
              records: const [],
              assetSummary: summary.assetSummary,
              dutySummary: summary.dutySummary,
              alerts: summary.alerts,
              onOpenAiLab: (intent) => capturedIntent = intent,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('打开 AI Lab').first);
    await tester.pumpAndSettle();

    expect(capturedIntent, isNotNull);
    expect(capturedIntent!.target, AiLabLaunchTarget.rag);
    expect(capturedIntent!.context?.workspaceTarget, 'ai_runtime');
    expect(capturedIntent!.context?.cardTarget, 'runtime_product');
    expect(capturedIntent!.sourceLabel, contains('资产台账'));
  });

  testWidgets(
    'History asset ledger dispatches knowledge ledger action into AI Lab',
    (tester) async {
      _setDesktopViewport(tester);
      AiLabLaunchIntent? capturedIntent;
      final summary = _buildSummary();
      final jobs = [
        JobRecord(
          jobId: 'rag-job-12345678',
          type: 'rag_ingest',
          status: 'succeeded',
          progress: 100,
          requestedBy: 'tester',
          attemptCount: 1,
          maxAttempts: 3,
          completedAt: DateTime(2026, 1, 1),
          input: const {
            'storage_path': 'docs/knowledge',
            'collection_name': 'ops-knowledge',
            'reset': true,
          },
          result: const {
            'storage_path': 'docs/knowledge',
            'collection': 'ops-knowledge',
            'count': 42,
          },
        ),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: HistoryAssetLedger(
                jobs: jobs,
                records: const [],
                assetSummary: summary.assetSummary,
                dutySummary: summary.dutySummary,
                alerts: summary.alerts,
                onOpenAiLab: (intent) => capturedIntent = intent,
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(
        find.text('回填知识入口'),
        500,
        scrollable: _verticalScrollable(),
      );
      await tester.tap(find.text('回填知识入口'));
      await tester.pumpAndSettle();

      expect(capturedIntent, isNotNull);
      expect(capturedIntent!.target, AiLabLaunchTarget.rag);
      expect(capturedIntent!.storagePath, 'docs/knowledge');
      expect(capturedIntent!.collectionName, 'ops-knowledge');
      expect(capturedIntent!.resetCollection, isTrue);
      expect(capturedIntent!.context?.workspaceTarget, 'ai_runtime');
      expect(capturedIntent!.context?.cardTarget, 'runtime_product');
      expect(capturedIntent!.sourceLabel, contains('知识库资产台账'));
    },
  );
}
