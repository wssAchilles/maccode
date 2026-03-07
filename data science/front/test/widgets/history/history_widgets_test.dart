import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/history_record.dart';
import 'package:front/widgets/history/history_record_card.dart';
import 'package:front/widgets/history/history_state_sections.dart';

HistoryRecord _buildRecord({
  String id = 'record-1',
  String filename = 'energy.csv',
  double? qualityScore = 88.5,
  String? createdAt = '2026-03-07T10:00:00',
}) {
  return HistoryRecord.fromJson({
    'id': id,
    'filename': filename,
    'quality_score': qualityScore,
    'created_at': createdAt,
  });
}

void main() {
  testWidgets('HistorySummaryBadge renders record count', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: HistorySummaryBadge(recordCount: 5)),
      ),
    );

    expect(find.text('共 5 条记录'), findsOneWidget);
  });

  testWidgets('HistoryErrorState renders message and triggers retry', (
    WidgetTester tester,
  ) async {
    var retried = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HistoryErrorState(
            message: '加载失败',
            onRetry: () => retried = true,
          ),
        ),
      ),
    );

    expect(find.text('加载失败'), findsOneWidget);

    await tester.tap(find.text('重试'));
    await tester.pump();

    expect(retried, isTrue);
  });

  testWidgets('HistoryEmptyState renders empty copy', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: HistoryEmptyState())),
    );

    expect(find.text('暂无历史记录'), findsOneWidget);
    expect(find.text('开始分析数据后，历史记录会显示在这里'), findsOneWidget);
  });

  testWidgets('HistoryRecordCard renders content and handles actions', (
    WidgetTester tester,
  ) async {
    var opened = false;
    var deleted = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HistoryRecordCard(
            record: _buildRecord(),
            isDeleting: false,
            onOpen: () => opened = true,
            onDelete: () => deleted = true,
          ),
        ),
      ),
    );

    expect(find.text('energy.csv'), findsOneWidget);
    expect(find.text('88.5'), findsOneWidget);
    expect(find.text('2026-03-07 10:00'), findsOneWidget);

    await tester.tap(find.text('energy.csv'));
    await tester.pump();
    expect(opened, isTrue);

    await tester.tap(find.byKey(const ValueKey('history-delete-record-1')));
    await tester.pump();
    expect(deleted, isTrue);
  });

  testWidgets('HistoryRecordCard disables delete while deleting', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HistoryRecordCard(
            record: _buildRecord(),
            isDeleting: true,
            onOpen: () {},
            onDelete: () {},
          ),
        ),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    final button = tester.widget<IconButton>(
      find.byKey(const ValueKey('history-delete-record-1')),
    );
    expect(button.onPressed, isNull);
  });
}
