import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/dashboard_summary.dart';
import 'package:front/models/job_record.dart';
import 'package:front/widgets/history/history_audit_overview.dart';

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
}
