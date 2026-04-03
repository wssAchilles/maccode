/// 规划任务仓储
library;

import '../models/control_task_record.dart';
import '../models/job_record.dart';
import '../services/api_service.dart';

abstract class ControlTaskRepository {
  Future<List<ControlTaskRecord>> listControlTasks({
    String? kind,
    bool? enabled,
    String? owner,
    int limit = 20,
  });

  Future<ControlTaskRecord> getControlTask(String controlTaskId);

  Future<JobRecord> runControlTask(
    String controlTaskId, {
    Map<String, dynamic>? input,
    String trigger = 'manual',
  });

  Future<ControlTaskRecord> setControlTaskEnabled(
    String controlTaskId, {
    required bool enabled,
  });

  Future<ControlTaskRecord> setControlTaskApprovalPolicy(
    String controlTaskId, {
    required Map<String, dynamic> approvalPolicy,
  });

  Future<ControlTaskRecord> updateControlTaskDefinition(
    String controlTaskId, {
    String? schedule,
    String? owner,
    required List<String> dependencies,
    required Map<String, dynamic> approvalPolicy,
    required Map<String, dynamic> defaultInput,
  });
}

class ApiControlTaskRepository implements ControlTaskRepository {
  const ApiControlTaskRepository();

  @override
  Future<List<ControlTaskRecord>> listControlTasks({
    String? kind,
    bool? enabled,
    String? owner,
    int limit = 20,
  }) async {
    final items = await ApiService.listControlTasks(
      kind: kind,
      enabled: enabled,
      owner: owner,
      limit: limit,
    );
    return items.map(ControlTaskRecord.fromJson).toList(growable: false);
  }

  @override
  Future<ControlTaskRecord> getControlTask(String controlTaskId) async {
    final payload = await ApiService.getControlTask(controlTaskId);
    return ControlTaskRecord.fromJson(payload);
  }

  @override
  Future<JobRecord> runControlTask(
    String controlTaskId, {
    Map<String, dynamic>? input,
    String trigger = 'manual',
  }) async {
    final payload = await ApiService.runControlTask(
      controlTaskId,
      input: input,
      trigger: trigger,
    );
    return JobRecord.fromJson(payload);
  }

  @override
  Future<ControlTaskRecord> setControlTaskEnabled(
    String controlTaskId, {
    required bool enabled,
  }) async {
    final payload = await ApiService.setControlTaskEnabled(
      controlTaskId,
      enabled: enabled,
    );
    return ControlTaskRecord.fromJson(payload);
  }

  @override
  Future<ControlTaskRecord> setControlTaskApprovalPolicy(
    String controlTaskId, {
    required Map<String, dynamic> approvalPolicy,
  }) async {
    final payload = await ApiService.setControlTaskApprovalPolicy(
      controlTaskId,
      approvalPolicy: approvalPolicy,
    );
    return ControlTaskRecord.fromJson(payload);
  }

  @override
  Future<ControlTaskRecord> updateControlTaskDefinition(
    String controlTaskId, {
    String? schedule,
    String? owner,
    required List<String> dependencies,
    required Map<String, dynamic> approvalPolicy,
    required Map<String, dynamic> defaultInput,
  }) async {
    final payload = await ApiService.updateControlTaskDefinition(
      controlTaskId,
      schedule: schedule,
      owner: owner,
      dependencies: dependencies,
      approvalPolicy: approvalPolicy,
      defaultInput: defaultInput,
    );
    return ControlTaskRecord.fromJson(payload);
  }
}
