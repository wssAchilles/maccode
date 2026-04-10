import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/job_record.dart';
import 'package:front/widgets/deep_learning/training_result_visual_panel.dart';

void main() {
  testWidgets('training result visual panel renders chart sections', (
    WidgetTester tester,
  ) async {
    final job = JobRecord.fromJson({
      'job_id': 'ml-train-1',
      'type': 'ml_train',
      'status': 'succeeded',
      'progress': 100,
      'requested_by': 'tester',
      'attempt_count': 1,
      'max_attempts': 3,
      'metadata': {'training_backend': 'vertex_custom_training'},
      'result': {
        'metrics': {
          'epochs_trained': 4,
          'train_loss': 0.18,
          'val_loss': 0.24,
          'train_mae': 0.09,
          'val_mae': 0.14,
          'training_samples': 128,
          'validation_samples': 32,
        },
        'history': {
          'loss': [0.48, 0.31, 0.22, 0.18],
          'val_loss': [0.56, 0.36, 0.28, 0.24],
          'mae': [0.28, 0.17, 0.11, 0.09],
          'val_mae': [0.33, 0.21, 0.16, 0.14],
        },
      },
    });

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: Center(
              child: SizedBox(
                width: 1200,
                child: DeepLearningTrainingResultPanel(job: job),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('训练结果可视化'), findsOneWidget);
    expect(find.text('损失收敛曲线'), findsOneWidget);
    expect(find.text('误差收敛曲线'), findsOneWidget);
    expect(find.text('误差热力块'), findsOneWidget);
    expect(find.text('样本分布'), findsOneWidget);
    expect(find.text('结果已收敛'), findsOneWidget);
  });
}
