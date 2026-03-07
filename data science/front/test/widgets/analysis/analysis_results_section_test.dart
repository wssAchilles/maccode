import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/analysis_result.dart';
import 'package:front/widgets/analysis/analysis_results_section.dart';

void main() {
  testWidgets('AnalysisResultsSection renders core analysis blocks', (
    WidgetTester tester,
  ) async {
    final result = AnalysisResult(
      basicInfo: BasicInfo(
        rows: 3,
        columns: 2,
        columnNames: const ['temperature', 'load'],
        columnTypes: const {'temperature': 'float64', 'load': 'int64'},
      ),
      preview: const [
        {'temperature': 25.5, 'load': 120},
        {'temperature': 26.1, 'load': 132},
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: AnalysisResultsSection(result: result),
          ),
        ),
      ),
    );

    expect(find.text('分析结果'), findsOneWidget);
    expect(find.text('基本信息'), findsOneWidget);
    expect(find.text('行数'), findsOneWidget);
    expect(find.text('3'), findsOneWidget);
    expect(find.text('数据预览 (前5行)'), findsOneWidget);
    expect(find.byType(DataTable), findsOneWidget);
  });

  testWidgets('AnalysisResultsSection aligns preview rows by column name', (
    WidgetTester tester,
  ) async {
    final result = AnalysisResult(
      basicInfo: BasicInfo(
        rows: 2,
        columns: 3,
        columnNames: const ['a', 'b', 'c'],
        columnTypes: const {'a': 'int64', 'b': 'int64', 'c': 'int64'},
      ),
      preview: const [
        {'b': 1, 'a': 2},
        {'c': 5, 'a': 3, 'b': 4},
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: AnalysisResultsSection(result: result),
          ),
        ),
      ),
    );

    final table = tester.widget<DataTable>(
      find.byKey(const ValueKey('analysis-preview-table')),
    );

    expect((table.columns[0].label as Text).data, 'a');
    expect((table.columns[1].label as Text).data, 'b');
    expect((table.columns[2].label as Text).data, 'c');

    expect((table.rows.first.cells[0].child as Text).data, '2');
    expect((table.rows.first.cells[1].child as Text).data, '1');
    expect((table.rows.first.cells[2].child as Text).data, '');

    expect((table.rows[1].cells[0].child as Text).data, '3');
    expect((table.rows[1].cells[1].child as Text).data, '4');
    expect((table.rows[1].cells[2].child as Text).data, '5');
  });
}
