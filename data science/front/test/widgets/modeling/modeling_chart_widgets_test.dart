import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/optimization_result.dart';
import 'package:front/widgets/power_chart_widget.dart';
import 'package:front/widgets/soc_chart_widget.dart';

List<ChartDataPoint> _buildChartData() {
  return [
    ChartDataPoint(
      hour: 0,
      datetime: '2026-03-07T00:00:00',
      load: 12,
      price: 0.25,
      batteryAction: 2,
      chargePower: 2,
      dischargePower: 0,
      soc: 45,
      storedEnergy: 20,
      gridPower: 14,
    ),
    ChartDataPoint(
      hour: 1,
      datetime: '2026-03-07T01:00:00',
      load: 13,
      price: 0.28,
      batteryAction: 1,
      chargePower: 1,
      dischargePower: 0,
      soc: 50,
      storedEnergy: 22,
      gridPower: 14,
    ),
    ChartDataPoint(
      hour: 18,
      datetime: '2026-03-07T18:00:00',
      load: 20,
      price: 1.0,
      batteryAction: -3,
      chargePower: 0,
      dischargePower: 3,
      soc: 40,
      storedEnergy: 18,
      gridPower: 17,
    ),
  ];
}

void main() {
  testWidgets('PowerChartWidget renders placeholder for empty chart data', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: PowerChartWidget(chartData: [])),
      ),
    );

    expect(find.text('暂无电网交互时序数据'), findsOneWidget);
  });

  testWidgets('PowerChartWidget shows non-empty legend and AI header', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 500,
            child: PowerChartWidget(chartData: _buildChartData()),
          ),
        ),
      ),
    );

    expect(find.text('AI 预测驱动'), findsOneWidget);
    expect(find.textContaining('阴影区域 = 削峰填谷效果'), findsOneWidget);
    expect(find.text('优化后电网'), findsOneWidget);
  });

  testWidgets('SocChartWidget renders placeholder for empty chart data', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: SocChartWidget(chartData: [])),
      ),
    );

    expect(find.text('暂无电池电量时序数据'), findsOneWidget);
  });

  testWidgets('SocChartWidget shows status and strategy explanation', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 500,
            child: SocChartWidget(chartData: _buildChartData()),
          ),
        ),
      ),
    );

    expect(find.text('📥 充电为主'), findsOneWidget);
    expect(find.textContaining('策略:'), findsOneWidget);
    expect(find.textContaining('0:00-2:00 低价充电'), findsOneWidget);
    expect(find.textContaining('18:00 高峰放电'), findsOneWidget);
  });
}
