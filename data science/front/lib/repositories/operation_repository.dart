/// 运行控制台仓储
library;

import '../models/job_record.dart';
import '../models/job_stream_frame.dart';
import '../services/api_service.dart';

abstract class OperationRepository {
  Future<List<JobRecord>> listOperations({
    String? type,
    String? status,
    int limit = 20,
  });

  Future<JobRecord> createOperation({
    required String type,
    required Map<String, dynamic> input,
    String? controlTaskId,
    String trigger = 'manual',
    Map<String, dynamic>? approvalPolicy,
    Map<String, dynamic>? metadata,
  });

  Future<JobRecord> getOperation(String operationId);

  Future<List<JobEvent>> getOperationEvents(
    String operationId, {
    int limit = 50,
  });

  Future<JobRecord> cancelOperation(String operationId);

  Future<JobRecord> retryOperation(String operationId);

  Future<JobRecord> approveOperation(
    String operationId, {
    required bool approved,
    String? message,
  });

  Stream<JobStreamFrame> streamOperation(
    String operationId, {
    double pollInterval = 2.0,
    double maxDuration = 55.0,
  });
}

class ApiOperationRepository implements OperationRepository {
  const ApiOperationRepository();

  @override
  Future<List<JobRecord>> listOperations({
    String? type,
    String? status,
    int limit = 20,
  }) async {
    final items = await ApiService.listOperations(
      type: type,
      status: status,
      limit: limit,
    );
    return items.map(JobRecord.fromJson).toList(growable: false);
  }

  @override
  Future<JobRecord> createOperation({
    required String type,
    required Map<String, dynamic> input,
    String? controlTaskId,
    String trigger = 'manual',
    Map<String, dynamic>? approvalPolicy,
    Map<String, dynamic>? metadata,
  }) async {
    final payload = await ApiService.createOperation(
      type: type,
      input: input,
      controlTaskId: controlTaskId,
      trigger: trigger,
      approvalPolicy: approvalPolicy,
      metadata: metadata,
    );
    return JobRecord.fromJson(payload);
  }

  @override
  Future<JobRecord> getOperation(String operationId) async {
    final payload = await ApiService.getOperation(operationId);
    return JobRecord.fromJson(payload);
  }

  @override
  Future<List<JobEvent>> getOperationEvents(
    String operationId, {
    int limit = 50,
  }) async {
    final items = await ApiService.getOperationEvents(
      operationId,
      limit: limit,
    );
    return items.map(JobEvent.fromJson).toList(growable: false);
  }

  @override
  Future<JobRecord> cancelOperation(String operationId) async {
    final payload = await ApiService.cancelOperation(operationId);
    return JobRecord.fromJson(payload);
  }

  @override
  Future<JobRecord> retryOperation(String operationId) async {
    final payload = await ApiService.retryOperation(operationId);
    return JobRecord.fromJson(payload);
  }

  @override
  Future<JobRecord> approveOperation(
    String operationId, {
    required bool approved,
    String? message,
  }) async {
    final payload = await ApiService.approveOperation(
      operationId,
      approved: approved,
      message: message,
    );
    return JobRecord.fromJson(payload);
  }

  @override
  Stream<JobStreamFrame> streamOperation(
    String operationId, {
    double pollInterval = 2.0,
    double maxDuration = 55.0,
  }) {
    return ApiService.streamOperation(
      operationId,
      pollInterval: pollInterval,
      maxDuration: maxDuration,
    );
  }
}
