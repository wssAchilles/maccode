/// 作业系统仓储
library;

import '../models/job_record.dart';
import '../models/job_stream_frame.dart';
import '../services/api_service.dart';

abstract class JobRepository {
  bool get supportsStreaming => false;

  Future<List<JobRecord>> listJobs({
    String? type,
    String? status,
    int limit = 20,
    String scope = 'private',
  });

  Future<JobRecord> getJob(String jobId);

  Future<JobRecord> retryJob(String jobId);

  Future<JobRecord> cancelJob(String jobId, {String? operationId}) {
    throw UnsupportedError('Cancel is not supported by this repository');
  }

  Future<JobRecord> approveJob(
    String jobId, {
    required bool approved,
    String? message,
    String? operationId,
  }) {
    throw UnsupportedError('Approval is not supported by this repository');
  }

  Stream<JobStreamFrame> streamJob(
    String jobId, {
    String? operationId,
  }) {
    throw UnsupportedError('Streaming is not supported by this repository');
  }

  Future<JobRecord> createOptimizationJob({
    required double initialSoc,
    DateTime? targetDate,
    double? batteryCapacity,
    double? batteryPower,
    double? batteryEfficiency,
    double? temperatureAdjust,
  });

  Future<JobRecord> createMlTrainJob({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    required String targetColumn,
  });

  Future<JobRecord> createRagIngestJob({
    required String storagePath,
    String? collectionName,
    bool reset = false,
  });
}

class ApiJobRepository implements JobRepository {
  const ApiJobRepository();

  @override
  bool get supportsStreaming => true;

  @override
  Future<List<JobRecord>> listJobs({
    String? type,
    String? status,
    int limit = 20,
    String scope = 'private',
  }) async {
    final items = await ApiService.listJobs(
      type: type,
      status: status,
      limit: limit,
      scope: scope,
    );
    return items.map(JobRecord.fromJson).toList(growable: false);
  }

  @override
  Future<JobRecord> getJob(String jobId) async {
    final payload = await ApiService.getJob(jobId);
    return JobRecord.fromJson(payload);
  }

  @override
  Future<JobRecord> retryJob(String jobId) async {
    final payload = await ApiService.retryJob(jobId);
    return JobRecord.fromJson(payload);
  }

  @override
  Future<JobRecord> cancelJob(String jobId, {String? operationId}) async {
    final payload = await ApiService.cancelOperation(operationId ?? jobId);
    return JobRecord.fromJson(payload);
  }

  @override
  Future<JobRecord> approveJob(
    String jobId, {
    required bool approved,
    String? message,
    String? operationId,
  }) async {
    final payload = await ApiService.approveOperation(
      operationId ?? jobId,
      approved: approved,
      message: message,
    );
    return JobRecord.fromJson(payload);
  }

  @override
  Stream<JobStreamFrame> streamJob(
    String jobId, {
    String? operationId,
  }) {
    return ApiService.streamOperation(operationId ?? jobId);
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
    final payload = await ApiService.createOptimizationJob(
      initialSoc: initialSoc,
      targetDate: targetDate,
      batteryCapacity: batteryCapacity,
      batteryPower: batteryPower,
      batteryEfficiency: batteryEfficiency,
      temperatureAdjust: temperatureAdjust,
    );
    return JobRecord.fromJson(payload);
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
    final payload = await ApiService.createMlTrainJob(
      storagePath: storagePath,
      modelType: modelType,
      epochs: epochs,
      batchSize: batchSize,
      windowSize: windowSize,
      targetColumn: targetColumn,
    );
    return JobRecord.fromJson(payload);
  }

  @override
  Future<JobRecord> createRagIngestJob({
    required String storagePath,
    String? collectionName,
    bool reset = false,
  }) async {
    final payload = await ApiService.createRagIngestJob(
      storagePath: storagePath,
      collectionName: collectionName,
      reset: reset,
    );
    return JobRecord.fromJson(payload);
  }
}
