import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/job_record.dart';
import 'package:front/utils/job_presentation.dart';

void main() {
  test('buildJobPrimaryText translates known backend status messages', () {
    const job = JobRecord(
      jobId: 'train-1',
      type: 'ml_train',
      status: 'running',
      progress: 35,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
      statusMessage: 'Loading training dataset',
    );

    expect(buildJobPrimaryText(job), '加载训练数据');
  });

  test('buildJobEventMessage translates known backend event messages', () {
    const job = JobRecord(
      jobId: 'train-1',
      type: 'ml_train',
      status: 'running',
      progress: 70,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
    );
    const event = JobEvent(
      phase: 'training',
      status: 'running',
      message: 'Training fallback neural regressor',
      progress: 70,
    );

    expect(buildJobEventMessage(job, event), '执行轻量回退训练');
  });

  test('buildJobEventMessage translates sequence preparation events', () {
    const job = JobRecord(
      jobId: 'train-2',
      type: 'ml_train',
      status: 'running',
      progress: 25,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
    );
    const event = JobEvent(
      phase: 'progress',
      status: 'running',
      message: 'Preparing sequence data',
      progress: 25,
    );

    expect(buildJobEventMessage(job, event), '准备序列数据');
  });

  test('buildJobEventMessage translates known rag backend event messages', () {
    const job = JobRecord(
      jobId: 'rag-1',
      type: 'rag_ingest',
      status: 'running',
      progress: 82,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
    );
    const event = JobEvent(
      phase: 'embedding',
      status: 'running',
      message: 'Creating embeddings and persisting vectors',
      progress: 82,
    );

    expect(buildJobEventMessage(job, event), '写入向量索引');
  });

  test(
    'buildJobEventMessage translates known optimization backend messages',
    () {
      const job = JobRecord(
        jobId: 'opt-1',
        type: 'optimization',
        status: 'running',
        progress: 76,
        requestedBy: 'tester',
        attemptCount: 1,
        maxAttempts: 3,
      );
      const event = JobEvent(
        phase: 'aggregation',
        status: 'running',
        message: 'Aggregating schedule and cost summary',
        progress: 76,
      );

      expect(buildJobEventMessage(job, event), '汇总调度与成本摘要');
    },
  );

  test('buildJobEventMessage translates vertex queue phases', () {
    const job = JobRecord(
      jobId: 'train-3',
      type: 'ml_train',
      status: 'running',
      progress: 15,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
    );
    const event = JobEvent(
      phase: 'vertex_queue',
      status: 'running',
      message: 'Vertex training job queued',
      progress: 15,
    );

    expect(buildJobEventMessage(job, event), 'Vertex 训练任务已排队');
  });
}
