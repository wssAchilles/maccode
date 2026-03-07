import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/analysis_result.dart';
import 'package:front/widgets/analysis/correlation_matrix_view.dart';
import 'package:front/widgets/analysis/statistical_panel.dart';

void main() {
  testWidgets(
    'CorrelationMatrixView tolerates incomplete high-correlation pairs and shows empty state for all-error results',
    (WidgetTester tester) async {
      final correlationResult = CorrelationResult.fromJson({
        'success': true,
        'high_correlations': [
          {
            'variables': ['load'],
            'correlation': 0.82,
            'type': 'pearson',
          },
        ],
        'correlations': [
          {
            'variable_x': 'load',
            'variable_y': 'temperature',
            'error': 'insufficient samples',
          },
        ],
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 360,
              child: CorrelationMatrixView(
                correlationResult: correlationResult,
                isMobile: true,
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.text('load ↔️ 未知变量'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('correlation-empty-state')),
        findsOneWidget,
      );
      expect(find.text('相关性详情暂不可展示'), findsOneWidget);
    },
  );

  testWidgets(
    'StatisticalPanel renders narrow summary layout without overflow',
    (WidgetTester tester) async {
      final statisticalResult = StatisticalResult.fromJson({
        'success': true,
        'summary': {
          'total_numeric_columns': 8,
          'normal_distribution_count': 3,
          'non_normal_distribution_count': 5,
        },
        'suggestions': ['优先使用非参数检验'],
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: SizedBox(
                width: 280,
                child: StatisticalPanel(statisticalResult: statisticalResult),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(
        find.byKey(const ValueKey('statistical-summary-section')),
        findsOneWidget,
      );
      expect(find.text('总列数'), findsOneWidget);
      expect(find.text('正态分布'), findsOneWidget);
      expect(find.text('非正态'), findsOneWidget);
    },
  );

  testWidgets(
    'StatisticalPanel shows empty state when success payload has no sections',
    (WidgetTester tester) async {
      final statisticalResult = StatisticalResult.fromJson({'success': true});

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: StatisticalPanel(statisticalResult: statisticalResult),
          ),
        ),
      );

      expect(
        find.byKey(const ValueKey('statistical-empty-state')),
        findsOneWidget,
      );
      expect(find.text('暂无统计检验结果'), findsOneWidget);
    },
  );
}
