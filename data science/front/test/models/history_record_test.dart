import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/history_record.dart';

void main() {
  test('fromJson falls back to nested summary quality score', () {
    final record = HistoryRecord.fromJson({
      'id': 'history-1',
      'filename': 'demo.csv',
      'summary': {
        'quality_analysis': {'success': true, 'quality_score': 88.5},
      },
    });

    expect(record.qualityScore, 88.5);
  });

  test('correlations getter supports current history summary key', () {
    final record = HistoryRecord.fromJson({
      'id': 'history-2',
      'filename': 'demo.csv',
      'summary': {
        'correlations': {'success': true, 'high_correlations': []},
      },
    });

    expect(record.correlations?['success'], isTrue);
  });
}
