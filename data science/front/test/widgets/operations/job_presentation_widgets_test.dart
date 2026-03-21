import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/job_record.dart';
import 'package:front/widgets/operations/job_event_timeline.dart';
import 'package:front/widgets/operations/job_progress_card.dart';

void main() {
  testWidgets('JobProgressCard localizes generic status messages', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: JobProgressCard(
            job: JobRecord(
              jobId: 'train-1',
              type: 'ml_train',
              status: 'succeeded',
              progress: 100,
              requestedBy: 'tester',
              attemptCount: 1,
              maxAttempts: 3,
              statusMessage: 'Job completed',
            ),
          ),
        ),
      ),
    );

    expect(find.text('Job completed'), findsNothing);
    expect(find.text('训练任务已完成'), findsOneWidget);
  });

  testWidgets('JobEventTimeline localizes generic event messages', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1400, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: JobEventTimeline(
              job: JobRecord(
                jobId: 'train-1',
                type: 'ml_train',
                status: 'succeeded',
                progress: 100,
                requestedBy: 'tester',
                attemptCount: 1,
                maxAttempts: 3,
                statusMessage: 'Job completed',
                events: const [
                  JobEvent(
                    phase: 'completed',
                    status: 'succeeded',
                    message: 'Job completed',
                    progress: 100,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Job completed'), findsNothing);
    expect(find.text('训练任务已完成'), findsWidgets);
  });
}
