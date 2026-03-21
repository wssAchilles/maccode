import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/dashboard_summary.dart';
import 'package:front/models/job_record.dart';
import 'package:front/widgets/history/history_audit_overview.dart';
import 'package:front/widgets/operations/duty_context_board.dart';

void main() {
  testWidgets('HistoryAuditOverview emits selected running status filter', (
    WidgetTester tester,
  ) async {
    String? selectedStatus;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HistoryAuditOverview(
            kpis: const DashboardKpis(
              datasetCount: 3,
              analysisCount: 2,
              modelCount: 1,
              jobs24h: 5,
              failedJobs: 1,
            ),
            jobs: const <JobRecord>[],
            activityCount: 4,
            recordCount: 3,
            selectedType: null,
            selectedStatus: null,
            onTypeChanged: (_) {},
            onStatusChanged: (value) => selectedStatus = value,
            onClearFilters: () {},
          ),
        ),
      ),
    );

    await tester.tap(find.widgetWithText(ChoiceChip, '运行中'));
    await tester.pump();

    expect(selectedStatus, 'running');
  });

  testWidgets('HistoryAuditOverview clear button triggers reset callback', (
    WidgetTester tester,
  ) async {
    var cleared = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HistoryAuditOverview(
            kpis: const DashboardKpis(
              datasetCount: 3,
              analysisCount: 2,
              modelCount: 1,
              jobs24h: 5,
              failedJobs: 1,
            ),
            jobs: const <JobRecord>[],
            activityCount: 4,
            recordCount: 3,
            selectedType: 'ml_train',
            selectedStatus: 'failed',
            onTypeChanged: (_) {},
            onStatusChanged: (_) {},
            onClearFilters: () => cleared = true,
          ),
        ),
      ),
    );

    await tester.tap(find.widgetWithText(OutlinedButton, '清空'));
    await tester.pump();

    expect(cleared, isTrue);
  });

  testWidgets('HistoryAuditOverview forwards duty action taps', (
    WidgetTester tester,
  ) async {
    DutyAction? tappedAction;
    const action = DutyAction(
      command: 'open_workspace',
      label: '打开 AI Lab',
      tone: 'primary',
      chainKey: 'model',
      chainLabel: '模型资产',
      workspaceTarget: 'ai_runtime',
      workspaceTargetLabel: 'AI 运行控制区',
      cardTarget: 'runtime_product',
      cardTargetLabel: '运行产物',
      incidentTarget: 'runtime',
      incidentTargetLabel: '运行态',
      workspaceBrief: 'AI Lab 训练车道 · 提交训练任务并跟进队列、产物与模型资产。',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HistoryAuditOverview(
            kpis: const DashboardKpis(
              datasetCount: 3,
              analysisCount: 2,
              modelCount: 1,
              jobs24h: 5,
              failedJobs: 1,
            ),
            jobs: const <JobRecord>[],
            dutyActions: const [action],
            activityCount: 4,
            recordCount: 3,
            selectedType: null,
            selectedStatus: null,
            onTypeChanged: (_) {},
            onStatusChanged: (_) {},
            onClearFilters: () {},
            onDutyAction: (value) => tappedAction = value,
          ),
        ),
      ),
    );

    await tester.tap(find.text('打开 AI Lab'));
    await tester.pump();

    expect(tappedAction, isNotNull);
    expect(tappedAction?.command, 'open_workspace');
    expect(tappedAction?.chainKey, 'model');
  });

  testWidgets('HistoryAuditOverview hides generic duty fact chips', (
    WidgetTester tester,
  ) async {
    const dutySummary = DutySummary(
      incidentCount: 1,
      activeCount: 0,
      watchCount: 0,
      overdueCount: 0,
      escalatedCount: 0,
      alertCount: 0,
      degradedSystemCount: 0,
      focusChainKey: 'model',
      focusChainLabel: '模型资产',
      focusWorkspaceTarget: 'ai_runtime',
      focusWorkspaceTargetLabel: 'AI 运行控制区',
      focusCardTarget: 'summary',
      focusCardTargetLabel: '当前卡片',
      focusIncidentTarget: 'sla',
      focusIncidentTargetLabel: '值班时限',
      focusWatch: '请优先处理模型资产链路',
      focusOwnerLabel: '--',
      focusEscalationStateLabel: '--',
      overviewActions: [],
      auditActions: [],
    );

    final assetSummary = AssetSummary.fromJson({
      'inventory': {
        'dataset_assets': 0,
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
          'card_target': 'summary',
          'card_target_label': '当前卡片',
          'incident_target': 'sla',
          'incident_target_label': '值班时限',
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
    });

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HistoryAuditOverview(
            kpis: const DashboardKpis(
              datasetCount: 3,
              analysisCount: 2,
              modelCount: 1,
              jobs24h: 5,
              failedJobs: 1,
            ),
            jobs: const <JobRecord>[],
            dutySummary: dutySummary,
            assetSummary: assetSummary,
            activityCount: 4,
            recordCount: 3,
            selectedType: null,
            selectedStatus: null,
            onTypeChanged: (_) {},
            onStatusChanged: (_) {},
            onClearFilters: () {},
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    final board = find.byType(DutyContextBoard);
    expect(
      find.descendant(of: board, matching: find.text('卡片 · 当前卡片')),
      findsNothing,
    );
    expect(
      find.descendant(of: board, matching: find.text('值班 · 值班时限')),
      findsNothing,
    );
  });
}
