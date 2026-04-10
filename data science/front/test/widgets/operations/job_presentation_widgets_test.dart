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

  testWidgets(
    'JobEventTimeline renders approval and cancel controls when available',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1400, 1200));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: Column(
                children: [
                  JobEventTimeline(
                    job: const JobRecord(
                      jobId: 'approval-1',
                      type: 'ml_train',
                      status: 'awaiting_approval',
                      progress: 0,
                      requestedBy: 'tester',
                      attemptCount: 0,
                      maxAttempts: 3,
                      approvalState: JobApprovalState(
                        required: true,
                        state: 'pending',
                        reason: 'needs approval',
                      ),
                    ),
                    onApprove: () {},
                    onReject: () {},
                  ),
                  JobEventTimeline(
                    job: const JobRecord(
                      jobId: 'running-1',
                      type: 'analysis',
                      status: 'running',
                      progress: 30,
                      requestedBy: 'tester',
                      attemptCount: 1,
                      maxAttempts: 3,
                    ),
                    onCancel: () {},
                  ),
                ],
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('批准执行'), findsOneWidget);
      expect(find.text('驳回任务'), findsOneWidget);
      expect(find.text('取消任务'), findsOneWidget);
    },
  );

  testWidgets(
    'JobProgressCard renders vertex backend chips and external action',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: JobProgressCard(
              job: JobRecord.fromJson({
                'job_id': 'vertex-1',
                'type': 'ml_train',
                'status': 'running',
                'progress': 15,
                'requested_by': 'tester',
                'attempt_count': 1,
                'max_attempts': 3,
                'metadata': {
                  'training_backend': 'vertex_custom_training',
                  'external_job': {
                    'state': 'JOB_STATE_RUNNING',
                    'console_url':
                        'https://console.cloud.google.com/vertex-ai/jobs/1',
                  },
                },
              }),
            ),
          ),
        ),
      );

      expect(find.text('Vertex AI'), findsOneWidget);
      expect(find.text('训练中'), findsOneWidget);
      expect(find.text('打开 Vertex 作业'), findsOneWidget);
    },
  );
}
