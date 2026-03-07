import 'package:flutter_test/flutter_test.dart';
import 'package:front/models/analysis_result.dart';

void main() {
  group('AnalysisResult', () {
    test(
      'parses quality, correlation and statistical sections from barrel import',
      () {
        final result = AnalysisResult.fromJson({
          'basic_info': {
            'rows': 10,
            'columns': 2,
            'column_names': ['a', 'b'],
            'column_types': {'a': 'double', 'b': 'double'},
          },
          'preview': [
            {'a': 1, 'b': 2},
          ],
          'quality_analysis': {
            'success': true,
            'quality_score': 0.92,
            'missing_analysis': {
              'a': {'count': 1, 'percentage': 10, 'risk_level': 'low'},
            },
          },
          'correlations': {
            'success': true,
            'high_correlations': [
              {
                'variables': ['a', 'b'],
                'correlation': 0.88,
                'type': 'pearson',
              },
            ],
          },
          'statistical_tests': {
            'success': true,
            'normality_tests': {
              'a': {'test_name': 'shapiro', 'p_value': 0.2, 'is_normal': true},
            },
            'summary': {
              'total_numeric_columns': 2,
              'normal_distribution_count': 1,
              'non_normal_distribution_count': 1,
            },
          },
        });

        expect(result.basicInfo.rows, 10);
        expect(result.qualityAnalysis?.qualityScore, 0.92);
        expect(result.correlations?.highCorrelations?.first.variables, [
          'a',
          'b',
        ]);
        expect(result.statisticalTests?.summary?.totalNumericColumns, 2);
      },
    );

    test(
      'keeps failure payload details for quality and correlation errors',
      () {
        final result = AnalysisResult.fromJson({
          'basic_info': {'rows': 0, 'columns': 0},
          'preview': [],
          'quality_analysis': {
            'success': false,
            'error': 'quality unavailable',
            'message': 'downstream error',
          },
          'correlations': {'success': false, 'error': 'corr unavailable'},
        });

        expect(result.qualityAnalysis?.success, isFalse);
        expect(result.qualityAnalysis?.message, 'downstream error');
        expect(result.correlations?.success, isFalse);
        expect(result.correlations?.error, 'corr unavailable');
      },
    );
  });
}
