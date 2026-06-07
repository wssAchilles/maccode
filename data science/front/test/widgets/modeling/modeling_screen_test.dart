import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/optimization_result.dart';
import 'package:front/screens/modeling_screen.dart';
import 'package:front/services/optimization_gateway.dart';
import 'package:front/viewmodels/modeling_view_model.dart';

class _FakeOptimizationGateway implements OptimizationGateway {
  _FakeOptimizationGateway({this.response, this.error});

  final OptimizationResponse? response;
  final Object? error;

  @override
  Future<OptimizationResponse> runOptimization({
    double initialSoc = 0.5,
    DateTime? targetDate,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
  }) async {
    if (error != null) {
      throw error!;
    }

    if (response == null) {
      throw StateError('No fake response configured');
    }

    return response!;
  }
}

OptimizationResponse _buildOptimizationResponse({
  required bool success,
  String? message,
}) {
  return OptimizationResponse.fromJson({
    'success': success,
    ...?message == null ? null : <String, dynamic>{'message': message},
    'model_info': {
      'model_type': 'random_forest',
      'status': success ? 'active' : 'pending',
      'training_samples': 8760,
      'metrics': {'mape': 0.08, 'r2_score': 0.91},
      'auto_selection': {'enabled': true, 'winner': 'xgboost'},
      'training_config': {'use_log_transform': true},
      'validation_summary': {'method': 'TimeSeriesSplit', 'cv_folds': 5},
      'data_coverage': {'start': '2025-01-01', 'end': '2025-12-31'},
    },
    'optimization': {
      'status': success ? 'Optimal' : 'Failed',
      'chart_data': <dynamic>[],
      'summary': {
        'total_cost_without_battery': 1000,
        'total_cost_with_battery': 800,
        'savings': 200,
        'savings_percent': 20,
        'total_load': 5000,
        'total_charged': 800,
        'total_discharged': 700,
        'peak_load': 350,
        'min_load': 120,
        'avg_load': 210,
      },
      'strategy': {
        'charging_hours': [1, 2, 3],
        'discharging_hours': [18, 19],
        'charging_count': 3,
        'discharging_count': 2,
      },
    },
  });
}

void main() {
  testWidgets('ModelingScreen runs optimization and renders success state', (
    WidgetTester tester,
  ) async {
    final viewModel = ModelingViewModel(
      gateway: _FakeOptimizationGateway(
        response: _buildOptimizationResponse(success: true),
      ),
    );

    addTearDown(viewModel.dispose);

    await tester.pumpWidget(
      MaterialApp(
        home: ModelingScreen(
          viewModel: viewModel,
          nowBuilder: () => DateTime(2026, 3, 7),
        ),
      ),
    );

    final runButton = find.byKey(const ValueKey('modeling-run-button'));
    expect(runButton, findsOneWidget);

    await tester.ensureVisible(runButton);
    await tester.tap(runButton);
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('成本对比'), findsOneWidget);
    expect(find.textContaining('优化完成！节省 200.00 元'), findsOneWidget);
  });

  testWidgets(
    'ModelingScreen surfaces optimization errors from the view model',
    (WidgetTester tester) async {
      final viewModel = ModelingViewModel(
        gateway: _FakeOptimizationGateway(error: Exception('network down')),
      );

      addTearDown(viewModel.dispose);

      await tester.pumpWidget(
        MaterialApp(
          home: ModelingScreen(
            viewModel: viewModel,
            nowBuilder: () => DateTime(2026, 3, 7),
          ),
        ),
      );

      final runButton = find.byKey(const ValueKey('modeling-run-button'));
      await tester.ensureVisible(runButton);
      await tester.tap(runButton);
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.textContaining('network down'), findsWidgets);
    },
  );
}
