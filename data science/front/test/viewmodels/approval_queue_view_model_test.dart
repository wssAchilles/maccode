import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/job_record.dart';
import 'package:front/models/job_stream_frame.dart';
import 'package:front/repositories/job_repository.dart';
import 'package:front/viewmodels/approval_queue_view_model.dart';

class _FakeApprovalJobRepository implements JobRepository {
  _FakeApprovalJobRepository({List<JobRecord>? jobs})
    : _jobs = List<JobRecord>.from(jobs ?? const []);

  final List<JobRecord> _jobs;

  @override
  bool get supportsStreaming => false;

  @override
  Future<List<JobRecord>> listJobs({
    String? type,
    String? status,
    int limit = 20,
  }) async {
    return List<JobRecord>.from(_jobs);
  }

  @override
  Future<JobRecord> approveJob(
    String jobId, {
    required bool approved,
    String? message,
    String? operationId,
  }) async {
    final updated = JobRecord(
      jobId: jobId,
      operationId: operationId ?? jobId,
      type: 'ml_train',
      status: approved ? 'queued' : 'cancelled',
      progress: 0,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
      cancelRequested: !approved,
      approvalState: JobApprovalState(
        required: true,
        state: approved ? 'approved' : 'rejected',
        reason: 'needs approval',
        message: message,
      ),
    );
    _jobs.removeWhere((job) => job.jobId == jobId);
    return updated;
  }

  @override
  Future<JobRecord> cancelJob(String jobId, {String? operationId}) =>
      throw UnimplementedError();

  @override
  Future<JobRecord> createMlTrainJob({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    required String targetColumn,
  }) => throw UnimplementedError();

  @override
  Future<JobRecord> createOptimizationJob({
    required double initialSoc,
    DateTime? targetDate,
    double? batteryCapacity,
    double? batteryPower,
    double? batteryEfficiency,
    double? temperatureAdjust,
  }) => throw UnimplementedError();

  @override
  Future<JobRecord> createRagIngestJob({
    required String storagePath,
    String? collectionName,
    bool reset = false,
  }) => throw UnimplementedError();

  @override
  Future<JobRecord> getJob(String jobId) => throw UnimplementedError();

  @override
  Future<JobRecord> retryJob(String jobId) => throw UnimplementedError();

  @override
  Stream<JobStreamFrame> streamJob(String jobId, {String? operationId}) =>
      throw UnimplementedError();
}

void main() {
  test('ApprovalQueueViewModel loads awaiting-approval jobs', () async {
    final repository = _FakeApprovalJobRepository(
      jobs: const [
        JobRecord(
          jobId: 'approval-1',
          operationId: 'approval-1',
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
      ],
    );
    final viewModel = ApprovalQueueViewModel(repository: repository);

    await viewModel.initialize();

    expect(viewModel.jobs, hasLength(1));
    expect(viewModel.jobs.first.jobId, 'approval-1');
    expect(viewModel.errorMessage, isNull);
    viewModel.dispose();
  });

  test(
    'ApprovalQueueViewModel resolves approval and removes queue item',
    () async {
      final repository = _FakeApprovalJobRepository(
        jobs: const [
          JobRecord(
            jobId: 'approval-1',
            operationId: 'approval-1',
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
        ],
      );
      final viewModel = ApprovalQueueViewModel(repository: repository);

      await viewModel.initialize();
      final updated = await viewModel.resolve(
        viewModel.jobs.first,
        approved: true,
      );

      expect(updated, isNotNull);
      expect(updated!.status, 'queued');
      expect(viewModel.jobs, isEmpty);
      expect(viewModel.errorMessage, isNull);
      viewModel.dispose();
    },
  );
}
