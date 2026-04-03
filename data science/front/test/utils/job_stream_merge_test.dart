import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/job_record.dart';
import 'package:front/models/job_stream_frame.dart';
import 'package:front/utils/job_stream_merge.dart';

void main() {
  test('mergeJobStreamFrame applies state updates and current step', () {
    const current = JobRecord(
      jobId: 'op-1',
      operationId: 'op-1',
      type: 'analysis',
      status: 'running',
      progress: 10,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
    );

    const frame = JobStreamFrame(
      event: 'operation.state',
      data: {
        'status': 'running',
        'progress': 55,
        'current_step': {
          'phase': 'generate_report',
          'tool_name': 'generate_report',
          'status': 'running',
          'progress': 55,
          'message': 'Generating report',
        },
      },
    );

    final merged = mergeJobStreamFrame(current, frame);

    expect(merged.progress, 55);
    expect(merged.currentStep?.phase, 'generate_report');
    expect(merged.status, 'running');
  });

  test('mergeJobStreamFrame appends event and artifact payloads', () {
    const current = JobRecord(
      jobId: 'op-1',
      operationId: 'op-1',
      type: 'analysis',
      status: 'running',
      progress: 55,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
    );

    const frame = JobStreamFrame(
      event: 'artifact.published',
      data: {
        'type': 'artifact.published',
        'phase': 'artifact',
        'status': 'ready',
        'message': 'Artifact published: report',
        'progress': 80,
        'artifact': {
          'type': 'report',
          'name': 'Operation report',
          'uri': 'reports/analysis.md',
        },
      },
    );

    final merged = mergeJobStreamFrame(current, frame);

    expect(merged.events, hasLength(1));
    expect(merged.artifacts, hasLength(1));
    expect(merged.artifacts.single.name, 'Operation report');
    expect(merged.progress, 80);
  });
}
