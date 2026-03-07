import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:front/widgets/analysis/feature_importance_chart.dart';

void main() {
  testWidgets('Feature importance chart renders core content', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: FeatureImportanceChart(
            featureImportance: {
              'Temperature': 0.42,
              'Hour': 0.33,
              'Price': 0.25,
            },
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('特征重要性分析'), findsOneWidget);
    expect(find.textContaining('共 3 个特征'), findsOneWidget);
    expect(find.textContaining('温度'), findsWidgets);
  });
}
