import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/job_record.dart';
import 'package:front/models/job_stream_frame.dart';
import 'package:front/repositories/job_repository.dart';
import 'package:front/viewmodels/job_view_model.dart';

class _FakeJobRepository implements JobRepository {
  _FakeJobRepository({
    List<JobRecord>? jobs,
    this.streamFrames = const <JobStreamFrame>[],
    this.streaming = false,
  }) : _jobs = List<JobRecord>.from(jobs ?? const []);

  final List<JobRecord> _jobs;
  final List<JobStreamFrame> streamFrames;
  final bool streaming;

  @override
  bool get supportsStreaming => streaming;

  @override
  Future<List<JobRecord>> listJobs({
    String? type,
    String? status,
    int limit = 20,
    String scope = 'private',
  }) async {
    return List<JobRecord>.from(_jobs);
  }

  @override
  Future<JobRecord> getJob(String jobId) async {
    return _jobs.firstWhere((job) => job.jobId == jobId);
  }

  @override
  Future<JobRecord> retryJob(String jobId) async {
    final updated = _buildJob(
      jobId: jobId,
      status: 'queued',
      progress: 0,
      retryable: false,
    );
    _replace(updated);
    return updated;
  }

  @override
  Future<JobRecord> cancelJob(String jobId, {String? operationId}) async {
    final updated = _buildJob(
      jobId: jobId,
      operationId: operationId ?? jobId,
      status: 'cancelled',
      progress: 40,
      cancelRequested: true,
    );
    _replace(updated);
    return updated;
  }

  @override
  Future<JobRecord> approveJob(
    String jobId, {
    required bool approved,
    String? message,
    String? operationId,
  }) async {
    final updated = _buildJob(
      jobId: jobId,
      operationId: operationId ?? jobId,
      status: approved ? 'queued' : 'cancelled',
      progress: 0,
      approvalState: JobApprovalState(
        required: true,
        state: approved ? 'approved' : 'rejected',
        reason: 'needs approval',
        message: message,
      ),
      cancelRequested: !approved,
    );
    _replace(updated);
    return updated;
  }

  @override
  Future<JobRecord> createOptimizationJob({
    required double initialSoc,
    DateTime? targetDate,
    double? batteryCapacity,
    double? batteryPower,
    double? batteryEfficiency,
    double? temperatureAdjust,
  }) async {
    final created = _buildJob(jobId: 'opt-1', status: 'queued', progress: 0);
    _replace(created);
    return created;
  }

  @override
  Future<JobRecord> createMlTrainJob({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    required String targetColumn,
  }) async {
    final created = _buildJob(jobId: 'train-1', status: 'queued', progress: 0);
    _replace(created);
    return created;
  }

  @override
  Future<JobRecord> createRagIngestJob({
    required String storagePath,
    String? collectionName,
    bool reset = false,
  }) async {
    final created = _buildJob(jobId: 'rag-1', status: 'queued', progress: 0);
    _replace(created);
    return created;
  }

  @override
  Stream<JobStreamFrame> streamJob(String jobId, {String? operationId}) async* {
    for (final frame in streamFrames) {
      final current = _jobs.firstWhere(
        (job) => job.jobId == (operationId ?? jobId),
      );
      if (frame.isState) {
        _replace(
          _buildJob(
            jobId: operationId ?? jobId,
            operationId: operationId ?? jobId,
            status: frame.data['status']?.toString() ?? current.status,
            progress: frame.data['progress'] is int
                ? frame.data['progress'] as int
                : current.progress,
            currentStep: frame.data['current_step'] is Map<String, dynamic>
                ? JobStep.fromJson(
                    frame.data['current_step'] as Map<String, dynamic>,
                  )
                : current.currentStep,
          ),
        );
      } else if (frame.isClosed) {
        _replace(
          _buildJob(
            jobId: operationId ?? jobId,
            operationId: operationId ?? jobId,
            status: frame.data['status']?.toString() ?? current.status,
            progress: current.progress,
            currentStep: current.currentStep,
          ),
        );
      } else if (frame.isJobEvent) {
        final event = frame.jobEvent;
        if (event != null) {
          _replace(
            _buildJob(
              jobId: operationId ?? jobId,
              operationId: operationId ?? jobId,
              status: event.status,
              progress: event.progress,
              currentStep: event.step ?? current.currentStep,
            ),
          );
        }
      }
      yield frame;
    }
  }

  void _replace(JobRecord job) {
    _jobs.removeWhere((item) => item.jobId == job.jobId);
    _jobs.insert(0, job);
  }

  JobRecord _buildJob({
    required String jobId,
    String? operationId,
    required String status,
    required int progress,
    bool retryable = false,
    bool cancelRequested = false,
    JobApprovalState? approvalState,
    JobStep? currentStep,
  }) {
    return JobRecord(
      jobId: jobId,
      operationId: operationId ?? jobId,
      type: 'analysis',
      status: status,
      progress: progress,
      requestedBy: 'tester',
      attemptCount: 1,
      maxAttempts: 3,
      retryable: retryable,
      cancelRequested: cancelRequested,
      approvalState: approvalState,
      currentStep: currentStep,
    );
  }
}

void main() {
  test('cancelJob updates active job state without polling', () async {
    final repository = _FakeJobRepository(
      jobs: const [
        JobRecord(
          jobId: 'job-1',
          operationId: 'job-1',
          type: 'analysis',
          status: 'queued',
          progress: 0,
          requestedBy: 'tester',
          attemptCount: 1,
          maxAttempts: 3,
        ),
      ],
    );
    final viewModel = JobViewModel(repository: repository, delay: (_) async {});

    await viewModel.loadJobs();
    final cancelled = await viewModel.cancelJob(viewModel.jobs.first);

    expect(cancelled, isNotNull);
    expect(cancelled!.status, 'cancelled');
    expect(viewModel.activeJob?.status, 'cancelled');
    expect(viewModel.errorMessage, isNull);
    viewModel.dispose();
  });

  test(
    'resolveApproval promotes queued job and clears pending approval',
    () async {
      final repository = _FakeJobRepository(
        jobs: const [
          JobRecord(
            jobId: 'job-approval',
            operationId: 'job-approval',
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
      final viewModel = JobViewModel(
        repository: repository,
        delay: (_) async {},
      );

      await viewModel.loadJobs();
      final updated = await viewModel.resolveApproval(
        viewModel.jobs.first,
        approved: true,
      );

      expect(updated, isNotNull);
      expect(updated!.status, 'queued');
      expect(updated.approvalState?.state, 'approved');
      expect(viewModel.activeJob?.status, 'queued');
      expect(viewModel.errorMessage, isNull);
      viewModel.dispose();
    },
  );

  test(
    'startPolling consumes stream updates when repository supports streaming',
    () async {
      final repository = _FakeJobRepository(
        streaming: true,
        jobs: const [
          JobRecord(
            jobId: 'job-stream',
            operationId: 'job-stream',
            type: 'analysis',
            status: 'queued',
            progress: 0,
            requestedBy: 'tester',
            attemptCount: 1,
            maxAttempts: 3,
          ),
        ],
        streamFrames: const [
          JobStreamFrame(
            event: 'operation.state',
            data: {
              'status': 'running',
              'progress': 65,
              'current_step': {
                'phase': 'generate_report',
                'tool_name': 'generate_report',
                'status': 'running',
                'progress': 65,
                'message': 'Generating report',
              },
            },
          ),
          JobStreamFrame(
            event: 'operation.completed',
            data: {
              'type': 'operation.completed',
              'phase': 'completed',
              'status': 'succeeded',
              'message': 'Operation completed',
              'progress': 100,
            },
          ),
          JobStreamFrame(
            event: 'operation.closed',
            data: {'status': 'succeeded'},
          ),
        ],
      );

      final viewModel = JobViewModel(
        repository: repository,
        delay: (_) async {},
      );

      await viewModel.loadJobs();
      await viewModel.startPolling(interval: Duration.zero);

      expect(viewModel.activeJob, isNotNull);
      expect(viewModel.activeJob!.status, 'succeeded');
      expect(viewModel.activeJob!.progress, 100);
      expect(viewModel.activeJob!.currentStep?.phase, 'generate_report');
      viewModel.dispose();
    },
  );
}
