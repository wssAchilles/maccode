import 'package:flutter_test/flutter_test.dart';
import 'package:front/models/optimization_result.dart';

void main() {
  group('OptimizationResponse', () {
    test('parses nested optimization payload from barrel import', () {
      final result = OptimizationResponse.fromJson({
        'success': true,
        'optimization': {
          'status': 'Optimal',
          'chart_data': [
            {
              'hour': 1,
              'datetime': '2026-03-07T01:00:00',
              'load': '12.5',
              'price': 0.7,
              'battery_action': 2,
              'charge_power': 2,
              'discharge_power': 0,
              'soc': 60,
              'stored_energy': 30,
              'grid_power': '10.5',
            },
          ],
          'summary': {
            'total_cost_without_battery': 100,
            'total_cost_with_battery': 80,
            'savings': 20,
            'savings_percent': 20,
            'total_load': 240,
            'total_charged': 30,
            'total_discharged': 24,
            'peak_load': 18,
            'min_load': 6,
            'avg_load': 10,
          },
          'strategy': {
            'charging_hours': [1, 2],
            'discharging_hours': [18, 19],
            'charging_count': 2,
            'discharging_count': 2,
          },
          'diagnostics': {
            'runtime_sec': 1.23,
            'mip_gap': 0.01,
            'node_count': 3,
            'iter_count': 4,
          },
          'constraint_hits': {
            'soc_min_hits': '1',
            'soc_max_hits': 2,
            'max_charge_hits': 3.0,
            'max_discharge_hits': 4,
          },
        },
        'prediction': {
          'target_date': '2026-03-08',
          'avg_load': 12,
          'peak_load': 18,
          'min_load': 6,
        },
        'battery_config': {
          'capacity': 50,
          'max_power': 20,
          'efficiency': 0.95,
          'initial_soc': 40,
        },
        'model_info': {
          'model_type': 'xgboost',
          'status': 'active',
          'metrics': {'test_mae': 1.5, 'test_rmse': 2.2},
          'auto_selection': {
            'enabled': true,
            'candidates_evaluated': ['xgboost', 'lgbm'],
            'winner': 'xgboost',
            'improvement_over_baseline': '12%',
            'validation_method': 'TimeSeriesSplit',
            'cv_folds': 5,
          },
          'training_config': {
            'test_size': 0.2,
            'use_time_series_cv': true,
            'cv_folds': 5,
          },
        },
        'model_explainability': {
          'feature_importance': {'temp': 0.6, 'hour': 0.4},
          'interpretation': 'temperature dominates',
        },
      });

      expect(result.isSuccess, isTrue);
      expect(result.optimization?.hoursCount, 1);
      expect(result.optimization?.chartData.first.load, 12.5);
      expect(result.optimization?.constraintHits?.maxChargeHits, 3);
      expect(result.optimization?.summary.savingsFormatted, '20.00 元');
      expect(result.modelInfo?.usedTimeSeriesCV, isTrue);
      expect(result.modelInfo?.validationMethodFormatted, '时序交叉验证 (5折)');
      expect(result.modelExplainability?.topFeature, 'temp');
      expect(result.toJson()['success'], isTrue);
    });

    test('parses flexible metadata payloads without type crashes', () {
      final result = OptimizationResponse.fromJson({
        'success': true,
        'model_info': {
          'model_type': 'lgbm',
          'status': 'active',
          'training_samples': '512',
          'feature_count': 12.0,
          'feature_columns': ['temp', 42],
          'data_coverage': {
            'start': '2026-01-01',
            'end': '2026-01-31',
            'span_days': '30',
            'rows': '1440',
          },
          'validation_summary': {
            'method': 'HoldOut',
            'cv_folds': '4',
            'cv_scores': ['1.2', 1.4],
            'holdout_mae': '2.1',
            'holdout_rmse': '3.2',
          },
          'metrics': {'test_mae': '1.5', 'sample_count': '300'},
          'auto_selection': {
            'enabled': 'true',
            'candidates_evaluated': ['lgbm', 'xgboost'],
            'winner': 'lgbm',
            'improvement_over_baseline': '8%',
            'all_scores': {
              'lgbm': {'mae': '1.1'},
            },
            'validation_method': 'time_series_split',
            'cv_folds': '4',
            'cv_details': {
              'fold_1': {'mae': '1.1'},
            },
          },
          'training_config': {
            'test_size': '0.25',
            'random_state': '42',
            'time_series_split': '1',
            'cv_folds': '5',
            'use_log_transform': 'false',
            'remove_outliers': 'true',
            'hyperparameter_tuning': 1,
          },
        },
      });

      expect(result.modelInfo?.trainingSamples, 512);
      expect(result.modelInfo?.featureCount, 12);
      expect(result.modelInfo?.featureColumns, ['temp', '42']);
      expect(result.modelInfo?.dataCoverage?.rows, 1440);
      expect(result.modelInfo?.dataCoverage?.spanDays, 30);
      expect(result.modelInfo?.validationSummary?.cvFolds, 4);
      expect(result.modelInfo?.validationSummary?.cvScores, [1.2, 1.4]);
      expect(result.modelInfo?.metrics?.sampleCount, 300);
      expect(result.modelInfo?.usedTimeSeriesCV, isTrue);
      expect(result.modelInfo?.validationMethodFormatted, '时序交叉验证 (4折)');
      expect(result.modelInfo?.trainingConfig?.useTimeSeriesCV, isTrue);
      expect(result.modelInfo?.trainingConfig?.useLogTransform, isFalse);
      expect(result.modelInfo?.trainingConfig?.removeOutliers, isTrue);
      expect(result.modelInfo?.trainingConfig?.tuneHyperparameters, isTrue);
    });
  });
}
