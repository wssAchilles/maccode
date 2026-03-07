import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/analysis_result.dart';
import 'package:front/widgets/analysis/feature_importance_chart.dart';
import 'package:front/widgets/analysis/quality_dashboard.dart';

void main() {
  testWidgets('FeatureImportanceChart prefers caller-provided descriptions', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: FeatureImportanceChart(
            featureImportance: {'Temperature': 0.42, 'Hour': 0.33},
            featureDescriptions: {'Temperature': '室外温度', 'Hour': '小时段'},
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.textContaining('室外温度'), findsWidgets);
    expect(find.textContaining('小时段'), findsWidgets);
  });

  testWidgets('FeatureImportanceChart shows empty state for empty data', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: FeatureImportanceChart(featureImportance: {})),
      ),
    );

    expect(find.text('暂无特征重要性数据'), findsOneWidget);
  });

  testWidgets('FeatureImportanceChart expands on narrow layouts safely', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(320, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 320,
            child: FeatureImportanceChart(
              featureImportance: const {
                'Temperature': 0.50,
                'Hour': 0.40,
                'Price': 0.30,
                'Humidity': 0.20,
              },
              defaultVisibleCount: 2,
            ),
          ),
        ),
      ),
    );

    expect(find.textContaining('湿度'), findsNothing);

    await tester.tap(find.byKey(const ValueKey('feature-importance-toggle')));
    await tester.pumpAndSettle();

    expect(find.textContaining('湿度'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'QualityDashboard renders warning chips without delete affordance',
    (WidgetTester tester) async {
      final qualityAnalysis = QualityAnalysis(
        success: true,
        qualityScore: 72,
        highRiskColumns: const ['load'],
        qualityMetrics: QualityMetrics(
          totalCells: 100,
          totalMissing: 8,
          missingRate: 8,
          totalOutliers: 2,
          duplicateRows: 1,
        ),
        recommendations: const ['补齐缺失值'],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: QualityDashboard(qualityAnalysis: qualityAnalysis),
            ),
          ),
        ),
      );

      final chip = tester.widget<Chip>(find.byType(Chip).first);
      expect(chip.onDeleted, isNull);
      expect(find.text('高风险列 (缺失率>5%)'), findsOneWidget);
      expect(find.text('补齐缺失值'), findsOneWidget);
    },
  );

  testWidgets('QualityDashboard clamps out-of-range score safely', (
    WidgetTester tester,
  ) async {
    final qualityAnalysis = QualityAnalysis(
      success: true,
      qualityScore: 120,
      qualityMetrics: QualityMetrics(
        totalCells: 100,
        totalMissing: 0,
        missingRate: 0,
        totalOutliers: 0,
        duplicateRows: 0,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: QualityDashboard(qualityAnalysis: qualityAnalysis),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('quality-dashboard-score')),
      findsOneWidget,
    );
    expect(find.text('100.0'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('QualityDashboard shows empty details placeholder', (
    WidgetTester tester,
  ) async {
    final qualityAnalysis = QualityAnalysis(success: true, qualityScore: 88);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: QualityDashboard(qualityAnalysis: qualityAnalysis),
        ),
      ),
    );

    expect(
      find.byKey(const ValueKey('quality-dashboard-empty-details')),
      findsOneWidget,
    );
    expect(find.text('暂无详细质量指标'), findsOneWidget);
  });
}
