import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/modeling_controls_state.dart';
import 'package:front/widgets/modeling/modeling_control_panel.dart';

void main() {
  testWidgets('ModelingControlPanel toggles callbacks and advanced state', (
    WidgetTester tester,
  ) async {
    var toggleCount = 0;
    var runCount = 0;
    ModelingScenario? selectedScenario;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ModelingControlPanel(
              state: ModelingControlsState.initial(
                now: DateTime(2026, 3, 7),
              ).copyWith(showAdvancedParams: true),
              isLoading: false,
              onToggleAdvancedParams: () => toggleCount += 1,
              onScenarioChanged: (scenario) => selectedScenario = scenario,
              onInitialSocChanged: (_) {},
              onBatteryCapacityChanged: (_) {},
              onMaxPowerChanged: (_) {},
              onTemperatureAdjustChanged: (_) {},
              onSelectDate: () {},
              onRunOptimization: () => runCount += 1,
            ),
          ),
        ),
      ),
    );

    expect(find.text('电池容量 (商业微网)'), findsOneWidget);
    expect(find.text('温度调整 (What-If)'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('modeling-toggle-advanced')));
    await tester.pump();
    expect(toggleCount, 1);

    await tester.tap(find.byKey(const ValueKey('modeling-scenario-summer')));
    await tester.pump();
    expect(selectedScenario, ModelingScenario.summer);

    await tester.tap(find.byKey(const ValueKey('modeling-run-button')));
    await tester.pump();
    expect(runCount, 1);
  });

  testWidgets('ModelingControlPanel stays stable on narrow layouts', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(360, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 360,
            child: SingleChildScrollView(
              child: ModelingControlPanel(
                state: ModelingControlsState.initial(now: DateTime(2026, 3, 7))
                    .copyWith(
                      showAdvancedParams: true,
                      selectedScenario: ModelingScenario.summer,
                      temperatureAdjust: 5,
                    ),
                isLoading: false,
                onToggleAdvancedParams: () {},
                onScenarioChanged: (_) {},
                onInitialSocChanged: (_) {},
                onBatteryCapacityChanged: (_) {},
                onMaxPowerChanged: (_) {},
                onTemperatureAdjustChanged: (_) {},
                onSelectDate: () {},
                onRunOptimization: () {},
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('目标日期'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('modeling-summary-banner')),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('ModelingControlPanel disables interactions while loading', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ModelingControlPanel(
              state: ModelingControlsState.initial(
                now: DateTime(2026, 3, 7),
              ).copyWith(showAdvancedParams: true),
              isLoading: true,
              onToggleAdvancedParams: () {},
              onScenarioChanged: (_) {},
              onInitialSocChanged: (_) {},
              onBatteryCapacityChanged: (_) {},
              onMaxPowerChanged: (_) {},
              onTemperatureAdjustChanged: (_) {},
              onSelectDate: () {},
              onRunOptimization: () {},
            ),
          ),
        ),
      ),
    );

    expect(
      tester.widget<ElevatedButton>(find.byType(ElevatedButton)).onPressed,
      isNull,
    );
    expect(
      tester
          .widget<FilterChip>(
            find.byKey(const ValueKey('modeling-scenario-summer')),
          )
          .onSelected,
      isNull,
    );
    expect(tester.widget<Slider>(find.byType(Slider).first).onChanged, isNull);
    expect(
      tester
          .widget<InkWell>(find.byKey(const ValueKey('modeling-select-date')))
          .onTap,
      isNull,
    );
  });
}
