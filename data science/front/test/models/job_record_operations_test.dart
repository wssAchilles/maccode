import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/job_record.dart';

void main() {
  test('JobRecord parses operation control-plane fields', () {
    final record = JobRecord.fromJson({
      'job_id': 'op-1',
      'operation_id': 'op-1',
      'type': 'analysis',
      'status': 'awaiting_approval',
      'progress': 42,
      'requested_by': 'tester',
      'attempt_count': 1,
      'max_attempts': 3,
      'control_task_id': 'analysis_manual',
      'trigger': 'manual',
      'cancel_requested': true,
      'current_step': {
        'phase': 'prepare_dataset',
        'tool_name': 'prepare_dataset',
        'status': 'running',
        'progress': 42,
        'message': 'Preparing dataset',
        'execution_target': 'light_worker',
        'retry_policy': {'max_attempts': 2},
        'artifact_policy': {'publish': true},
      },
      'steps': [
        {
          'phase': 'prepare_dataset',
          'tool_name': 'prepare_dataset',
          'status': 'running',
          'progress': 42,
          'message': 'Preparing dataset',
          'execution_target': 'light_worker',
          'concurrency_key': 'dataset',
        },
      ],
      'artifacts': [
        {
          'type': 'report',
          'name': 'Operation report',
          'uri': 'reports/analysis.md',
          'created_at': '2026-04-03T00:00:00+00:00',
        },
      ],
      'approval_state': {
        'required': true,
        'state': 'pending',
        'reason': 'manual approval required',
      },
      'approval_policy': {'required': true, 'mode': 'manual'},
      'metrics': {'runtime_ms': 3210},
      'events': [
        {
          'type': 'step.started',
          'phase': 'prepare_dataset',
          'status': 'running',
          'message': 'Preparing dataset',
          'progress': 42,
        },
      ],
    });

    expect(record.operationId, 'op-1');
    expect(record.controlTaskId, 'analysis_manual');
    expect(record.trigger, 'manual');
    expect(record.cancelRequested, isTrue);
    expect(record.requiresApproval, isTrue);
    expect(record.isAwaitingApproval, isTrue);
    expect(record.currentStep?.toolName, 'prepare_dataset');
    expect(record.currentStep?.executionTarget, 'light_worker');
    expect(record.steps.single.concurrencyKey, 'dataset');
    expect(record.artifacts.single.name, 'Operation report');
    expect(record.metrics['runtime_ms'], 3210);
    expect(record.events.single.type, 'step.started');
  });

  test('JobRecord exposes scheduled operation display titles', () {
    const fetchRecord = JobRecord(
      jobId: 'fetch-1',
      type: 'fetch_data',
      status: 'queued',
      progress: 0,
      requestedBy: 'system',
      attemptCount: 0,
      maxAttempts: 1,
    );
    const trainRecord = JobRecord(
      jobId: 'train-1',
      type: 'train_model',
      status: 'queued',
      progress: 0,
      requestedBy: 'system',
      attemptCount: 0,
      maxAttempts: 1,
    );

    expect(fetchRecord.displayTitle, '小时数据抓取');
    expect(trainRecord.displayTitle, '每日模型重训');
  });

  test('JobRecord parses vertex training metadata fields', () {
    final record = JobRecord.fromJson({
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
          'state': 'JOB_STATE_PENDING',
          'console_url': 'https://console.cloud.google.com/vertex-ai/jobs/1',
        },
        'budget_guard': {
          'max_runtime_s': 7200,
          'max_parallel_jobs': 2,
          'cpu_only': true,
        },
      },
    });

    expect(record.trainingBackend, 'vertex_custom_training');
    expect(record.isVertexTraining, isTrue);
    expect(record.externalJobState, 'JOB_STATE_PENDING');
    expect(
      record.externalJobConsoleUrl,
      'https://console.cloud.google.com/vertex-ai/jobs/1',
    );
    expect(record.budgetGuard['cpu_only'], isTrue);
  });
}
