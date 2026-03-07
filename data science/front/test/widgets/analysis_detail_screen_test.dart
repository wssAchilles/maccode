import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/history_record.dart';
import 'package:front/screens/analysis_detail_screen.dart';

HistoryRecord _buildRecord() {
  return HistoryRecord.fromJson({
    'id': 'record-1',
    'filename': 'energy.csv',
    'created_at': '2026-03-07T10:00:00Z',
    'summary': {
      'basic_info': {
        'rows': 120,
        'columns': 3,
        'column_types': {'temp': 'float64', 'load': 'float64', 'hour': 'int64'},
      },
      'quality_analysis': {
        'success': true,
        'quality_score': 91.2,
        'quality_metrics': {
          'missing_rate': 1.5,
          'total_outliers': 2,
          'duplicate_rows': 0,
        },
        'high_risk_columns': ['temp'],
        'recommendations': ['补充 temp 的缺失值'],
      },
      'correlations': {
        'success': true,
        'high_correlations': [
          {
            'variables': ['temp', 'load'],
            'correlation': 0.82,
            'type': 'positive',
          },
        ],
        'suggestions': ['关注温度与负载的共线性'],
      },
      'statistical_tests': {
        'success': true,
        'normality_tests': {
          'temp': {
            'is_normal': true,
            'p_value': 0.1234,
            'skewness': 0.1,
            'kurtosis': 0.2,
          },
        },
        'non_normal_columns': ['load'],
        'suggestions': ['对 load 做分布变换'],
      },
      'preview': {
        'columns': ['temp', 'load'],
        'data': [
          [20, 100],
          [21, 105],
        ],
      },
    },
  });
}

void main() {
  testWidgets('renders normalized history detail sections', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(home: AnalysisDetailScreen(record: _buildRecord())),
    );

    expect(find.text('数据质量评估'), findsOneWidget);
    expect(find.text('相关性分析'), findsOneWidget);
    expect(find.text('统计检验'), findsOneWidget);
    expect(find.text('数据集信息'), findsOneWidget);
    expect(find.text('数据预览'), findsOneWidget);
    expect(find.text('temp ↔ load'), findsOneWidget);
    expect(find.text('补充 temp 的缺失值'), findsOneWidget);
    expect(find.text('对 load 做分布变换'), findsOneWidget);
  });
}
