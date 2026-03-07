import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/optimization_result.dart';
import 'package:front/widgets/modeling/modeling_health_section.dart';
import 'package:front/widgets/modeling/optimization_insights_section.dart';

ModelInfo _buildModelInfo() {
  return ModelInfo.fromJson({
    'model_type': 'random_forest',
    'status': 'active',
    'trained_at': '2026-03-06T00:00:00Z',
    'training_samples': 8760,
    'data_source': 'CAISO',
    'metrics': {'mape': 0.08, 'r2_score': 0.91, 'test_mae': 5.2},
    'auto_selection': {
      'enabled': true,
      'candidates_evaluated': ['xgboost', 'random_forest'],
      'winner': 'xgboost',
      'improvement_over_baseline': '+8.0%',
      'validation_method': 'TimeSeriesSplit',
      'cv_folds': 5,
      'all_scores': {
        'xgboost': {'mae': 5.0},
        'random_forest': {'mae': 5.8},
      },
    },
    'training_config': {
      'use_log_transform': true,
      'remove_outliers': true,
      'hyperparameter_tuning': false,
      'use_time_series_cv': true,
    },
    'validation_summary': {
      'method': 'TimeSeriesSplit',
      'cv_folds': 5,
      'cv_mae_mean': 5.3,
      'cv_mae_std': 0.4,
      'holdout_mae': 5.4,
    },
    'data_coverage': {
      'start': '2025-01-01',
      'end': '2025-12-31',
      'span_days': 365,
      'rows': 8760,
    },
  });
}

ModelInfo _buildModelInfoWithoutMetrics() {
  return ModelInfo.fromJson({
    'model_type': 'random_forest',
    'status': 'inactive',
    'data_source': 'CAISO',
  });
}

OptimizationData _buildOptimizationData() {
  return OptimizationData.fromJson({
    'status': 'Optimal',
    'chart_data': [],
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
    'diagnostics': {
      'runtime_sec': 1.23,
      'mip_gap': 0.01,
      'node_count': 42,
      'iter_count': 128,
    },
    'constraint_hits': {
      'soc_min_hits': 2,
      'soc_max_hits': 1,
      'max_charge_hits': 4,
      'max_discharge_hits': 3,
    },
  });
}

OptimizationData _buildOptimizationDataWithoutDiagnostics() {
  return OptimizationData.fromJson({
    'status': 'Optimal',
    'chart_data': [],
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
  });
}

void main() {
  testWidgets('ModelingHealthCard renders key model health sections', (
    WidgetTester tester,
  ) async {
    final modelInfo = _buildModelInfo();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ModelingHealthCard(modelInfo: modelInfo),
          ),
        ),
      ),
    );

    expect(find.textContaining('AI 模型状态'), findsOneWidget);
    expect(find.text('运行中'), findsOneWidget);
    expect(find.textContaining('自动模型选择'), findsOneWidget);
    expect(find.textContaining('训练配置'), findsOneWidget);
    expect(find.text('验证与数据覆盖'), findsOneWidget);
  });

  testWidgets('ModelingHealthCard expands auto-selection score details', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ModelingHealthCard(modelInfo: _buildModelInfo()),
          ),
        ),
      ),
    );

    expect(find.text('MAE: 5.80 kW'), findsNothing);

    await tester.tap(
      find.byKey(const ValueKey('modeling-auto-selection-scores-toggle')),
    );
    await tester.pumpAndSettle();

    expect(find.text('MAE: 5.00 kW'), findsOneWidget);
    expect(find.text('MAE: 5.80 kW'), findsOneWidget);
  });

  testWidgets('SolverDiagnosticsCard renders diagnostics and constraint hits', (
    WidgetTester tester,
  ) async {
    final optimization = _buildOptimizationData();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: SolverDiagnosticsCard(optimization: optimization)),
      ),
    );

    expect(find.text('求解器健康度'), findsOneWidget);
    expect(find.textContaining('SOC 下限命中'), findsOneWidget);
    expect(find.textContaining('放电功率封顶'), findsOneWidget);
  });

  testWidgets('ModelingHealthCard shows placeholder when metrics are missing', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: ModelingHealthCard(
              modelInfo: _buildModelInfoWithoutMetrics(),
            ),
          ),
        ),
      ),
    );

    expect(find.text('暂无详细性能指标'), findsOneWidget);
    expect(find.text('待训练'), findsOneWidget);
  });

  testWidgets('SolverDiagnosticsCard hides itself without diagnostics data', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SolverDiagnosticsCard(
            optimization: _buildOptimizationDataWithoutDiagnostics(),
          ),
        ),
      ),
    );

    expect(find.text('求解器健康度'), findsNothing);
  });

  testWidgets('Optimization sections render metrics and strategy blocks', (
    WidgetTester tester,
  ) async {
    final optimization = _buildOptimizationData();
    final previousResult = OptimizationResponse.fromJson({
      'success': true,
      'optimization': {
        'status': 'Optimal',
        'chart_data': [],
        'summary': {
          'total_cost_without_battery': 1000,
          'total_cost_with_battery': 850,
          'savings': 150,
          'savings_percent': 15,
          'total_load': 5000,
          'total_charged': 800,
          'total_discharged': 700,
          'peak_load': 350,
          'min_load': 120,
          'avg_load': 210,
        },
        'strategy': {
          'charging_hours': [1],
          'discharging_hours': [18],
          'charging_count': 1,
          'discharging_count': 1,
        },
      },
    });

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: Column(
              children: [
                OptimizationMetricsSection(
                  optimization: optimization,
                  previousResult: previousResult,
                ),
                OptimizationStrategyDetailsCard(optimization: optimization),
              ],
            ),
          ),
        ),
      ),
    );

    expect(find.textContaining('优化效果'), findsOneWidget);
    expect(find.text('成本对比'), findsOneWidget);
    expect(find.textContaining('充放电策略'), findsOneWidget);
    expect(find.text('总计节省'), findsOneWidget);
    expect(find.textContaining('vs 上次'), findsOneWidget);
  });
}
