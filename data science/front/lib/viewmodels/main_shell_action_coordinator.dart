library;

import '../models/compute_rollout_policy.dart';
import '../models/control_task_record.dart';
import '../models/job_record.dart';
import '../models/shell_action_outcome.dart';
import '../models/workbench_runtime_models.dart';
import 'approval_queue_view_model.dart';
import 'compute_governance_view_model.dart';
import 'control_task_view_model.dart';
import 'dashboard_view_model.dart';
import 'job_feed_registry.dart';
import 'job_view_model.dart';
import 'operation_console_view_model.dart';

class MainShellActionCoordinator {
  const MainShellActionCoordinator({
    required DashboardViewModel dashboardViewModel,
    required ComputeGovernanceViewModel computeGovernanceViewModel,
    required ControlTaskViewModel controlTaskViewModel,
    required ApprovalQueueViewModel approvalQueueViewModel,
    required OperationConsoleViewModel operationConsoleViewModel,
    required JobFeedRegistry jobFeedRegistry,
  }) : _dashboardViewModel = dashboardViewModel,
       _computeGovernanceViewModel = computeGovernanceViewModel,
       _controlTaskViewModel = controlTaskViewModel,
       _approvalQueueViewModel = approvalQueueViewModel,
       _operationConsoleViewModel = operationConsoleViewModel,
       _jobFeedRegistry = jobFeedRegistry;

  final DashboardViewModel _dashboardViewModel;
  final ComputeGovernanceViewModel _computeGovernanceViewModel;
  final ControlTaskViewModel _controlTaskViewModel;
  final ApprovalQueueViewModel _approvalQueueViewModel;
  final OperationConsoleViewModel _operationConsoleViewModel;
  final JobFeedRegistry _jobFeedRegistry;

  Future<ShellActionOutcome<JobRecord>> runControlTask(
    ControlTaskRecord task, {
    Map<String, dynamic>? inputOverrides,
    String trigger = 'manual',
  }) async {
    final operation = await _controlTaskViewModel.runControlTask(
      task,
      inputOverrides: inputOverrides,
      trigger: trigger,
    );
    if (operation == null) {
      return ShellActionOutcome.failure(
        _controlTaskViewModel.errorMessage ?? '触发规划任务失败',
      );
    }

    await Future.wait([
      _controlTaskViewModel.loadControlTasks(),
      _approvalQueueViewModel.loadQueue(),
    ]);
    await _openOperation(operation);
    final awaitingApproval = operation.status == 'awaiting_approval';
    return ShellActionOutcome.success(
      awaitingApproval ? '已创建待审批运行: ${task.title}' : '已触发规划任务: ${task.title}',
      data: operation,
      tone: awaitingApproval
          ? ShellActionTone.warning
          : ShellActionTone.success,
    );
  }

  Future<ShellActionOutcome<ControlTaskRecord>> setControlTaskEnabled(
    ControlTaskRecord task, {
    required bool enabled,
  }) async {
    final updated = await _controlTaskViewModel.setControlTaskEnabled(
      task,
      enabled: enabled,
    );
    if (updated == null) {
      return ShellActionOutcome.failure(
        _controlTaskViewModel.errorMessage ?? '更新规划任务状态失败',
      );
    }
    return ShellActionOutcome.success(
      updated.enabled ? '已恢复规划任务: ${task.title}' : '已暂停规划任务: ${task.title}',
      data: updated,
      tone: updated.enabled ? ShellActionTone.success : ShellActionTone.warning,
    );
  }

  Future<ShellActionOutcome<ControlTaskRecord>> setControlTaskApprovalPolicy(
    ControlTaskRecord task, {
    required Map<String, dynamic> approvalPolicy,
  }) async {
    final updated = await _controlTaskViewModel.setControlTaskApprovalPolicy(
      task,
      approvalPolicy: approvalPolicy,
    );
    if (updated == null) {
      return ShellActionOutcome.failure(
        _controlTaskViewModel.errorMessage ?? '更新规划任务审批策略失败',
      );
    }
    final requiredApproval = updated.approvalPolicy['required'] == true;
    return ShellActionOutcome.success(
      requiredApproval ? '已切换为审批执行: ${task.title}' : '已切换为自动执行: ${task.title}',
      data: updated,
      tone: requiredApproval
          ? ShellActionTone.warning
          : ShellActionTone.success,
    );
  }

  Future<ShellActionOutcome<ControlTaskRecord>> updateControlTaskDefinition(
    ControlTaskRecord task, {
    String? schedule,
    String? owner,
    required List<String> dependencies,
    required Map<String, dynamic> approvalPolicy,
    required Map<String, dynamic> defaultInput,
  }) async {
    final updated = await _controlTaskViewModel.updateControlTaskDefinition(
      task,
      schedule: schedule,
      owner: owner,
      dependencies: dependencies,
      approvalPolicy: approvalPolicy,
      defaultInput: defaultInput,
    );
    if (updated == null) {
      return ShellActionOutcome.failure(
        _controlTaskViewModel.errorMessage ?? '更新规划任务定义失败',
      );
    }
    return ShellActionOutcome.success(
      '已更新规划任务定义: ${task.title}',
      data: updated,
    );
  }

  Future<ShellActionOutcome<JobRecord>> requestComputeRolloutModeChange(
    ComputeRolloutComponentPolicy component, {
    required Map<String, dynamic> targetPolicy,
    String? changeReason,
    String requestKind = 'rollout_change',
  }) async {
    final operation = await _computeGovernanceViewModel.requestRolloutModeChange(
      component.key,
      targetPolicy: targetPolicy,
      changeReason: changeReason,
      requestKind: requestKind,
    );
    if (operation == null) {
      return ShellActionOutcome.failure(
        _computeGovernanceViewModel.errorMessage ?? '提交计算治理变更失败',
      );
    }
    await _approvalQueueViewModel.loadQueue();
    await _openOperation(operation);
    return ShellActionOutcome.success(
      operation.isAwaitingApproval
          ? '已提交 ${component.label} 的治理变更，等待审批'
          : '已提交 ${component.label} 的治理运行',
      data: operation,
      tone: operation.isAwaitingApproval
          ? ShellActionTone.warning
          : ShellActionTone.success,
    );
  }

  Future<ShellActionOutcome<JobRecord>> requestComputeBenchmark(
    ComputeRolloutComponentPolicy component, {
    int sampleRows = 5000,
  }) async {
    final operation = await _computeGovernanceViewModel.requestBenchmark(
      component.key,
      sampleRows: sampleRows,
    );
    if (operation == null) {
      return ShellActionOutcome.failure(
        _computeGovernanceViewModel.errorMessage ?? '提交 benchmark 失败',
      );
    }
    await _openOperation(operation);
    return ShellActionOutcome.success(
      '已提交 ${component.label} 的 benchmark 运行',
      data: operation,
    );
  }

  Future<ShellActionOutcome<JobRecord>> resolveQueuedApproval(
    JobRecord job, {
    required bool approved,
    String? message,
  }) async {
    final updated = await _approvalQueueViewModel.resolve(
      job,
      approved: approved,
      message: message,
    );
    if (updated == null) {
      return ShellActionOutcome.failure(
        _approvalQueueViewModel.errorMessage ?? '审批操作失败',
      );
    }
    await Future.wait([
      _controlTaskViewModel.loadControlTasks(),
      _approvalQueueViewModel.loadQueue(),
    ]);
    await _openOperation(updated);
    return ShellActionOutcome.success(
      approved ? '已批准任务: ${job.displayTitle}' : '已驳回任务: ${job.displayTitle}',
      data: updated,
      tone: approved ? ShellActionTone.success : ShellActionTone.warning,
    );
  }

  Future<ShellActionOutcome<JobRecord>> resolveSelectedOperationApproval({
    required bool approved,
    String? message,
  }) async {
    final current = _operationConsoleViewModel.selectedOperation;
    if (current == null) {
      return ShellActionOutcome.failure('当前未选中运行');
    }
    final updated = await _operationConsoleViewModel.resolveSelectedApproval(
      approved: approved,
      message: message,
    );
    if (updated == null) {
      return ShellActionOutcome.failure(
        _operationConsoleViewModel.errorMessage ?? '审批操作失败',
      );
    }
    await Future.wait([
      _approvalQueueViewModel.loadQueue(),
      _controlTaskViewModel.loadControlTasks(),
    ]);
    return ShellActionOutcome.success(
      approved ? '已批准运行: ${current.displayTitle}' : '已驳回运行: ${current.displayTitle}',
      data: updated,
      tone: approved ? ShellActionTone.success : ShellActionTone.warning,
    );
  }

  Future<ShellActionOutcome<JobRecord>> retrySelectedOperation() async {
    final current = _operationConsoleViewModel.selectedOperation;
    if (current == null) {
      return ShellActionOutcome.failure('当前未选中运行');
    }
    final updated = await _operationConsoleViewModel.retrySelected();
    if (updated == null) {
      return ShellActionOutcome.failure(
        _operationConsoleViewModel.errorMessage ?? '重试运行失败',
      );
    }
    await _controlTaskViewModel.loadControlTasks();
    return ShellActionOutcome.success(
      '已重试运行: ${current.displayTitle}',
      data: updated,
    );
  }

  Future<ShellActionOutcome<JobRecord>> cancelSelectedOperation() async {
    final current = _operationConsoleViewModel.selectedOperation;
    if (current == null) {
      return ShellActionOutcome.failure('当前未选中运行');
    }
    final updated = await _operationConsoleViewModel.cancelSelected();
    if (updated == null) {
      return ShellActionOutcome.failure(
        _operationConsoleViewModel.errorMessage ?? '取消运行失败',
      );
    }
    await Future.wait([
      _controlTaskViewModel.loadControlTasks(),
      _approvalQueueViewModel.loadQueue(),
    ]);
    return ShellActionOutcome.success(
      '已取消运行: ${current.displayTitle}',
      data: updated,
      tone: ShellActionTone.warning,
    );
  }

  Future<ShellActionOutcome<JobRecord>> retrySharedJob(JobRecord job) async {
    final feed = _feedFor(job);
    if (feed == null) {
      return ShellActionOutcome.failure('当前任务不支持壳级重试');
    }
    final updated = await feed.retryJob(job.jobId);
    if (updated == null) {
      return ShellActionOutcome.failure(feed.errorMessage ?? '重试任务失败');
    }
    await _dashboardViewModel.loadSummary();
    await _openOperation(updated);
    return ShellActionOutcome.success(
      '已重试任务: ${job.displayTitle}',
      data: updated,
    );
  }

  Future<ShellActionOutcome<JobRecord>> cancelSharedJob(JobRecord job) async {
    final feed = _feedFor(job);
    if (feed == null) {
      return ShellActionOutcome.failure('当前任务不支持壳级取消');
    }
    final updated = await feed.cancelJob(job);
    if (updated == null) {
      return ShellActionOutcome.failure(feed.errorMessage ?? '取消任务失败');
    }
    await Future.wait([
      _dashboardViewModel.loadSummary(),
      if (job.controlTaskId != null) _controlTaskViewModel.loadControlTasks(),
      _approvalQueueViewModel.loadQueue(),
    ]);
    await _openOperation(updated);
    return ShellActionOutcome.success(
      '已取消任务: ${job.displayTitle}',
      data: updated,
      tone: ShellActionTone.warning,
    );
  }

  Future<ShellActionOutcome<JobRecord>> resolveSharedJobApproval(
    JobRecord job, {
    required bool approved,
    String? message,
  }) async {
    final feed = _feedFor(job);
    if (feed == null) {
      return ShellActionOutcome.failure('当前任务不支持壳级审批');
    }
    final updated = await feed.resolveApproval(
      job,
      approved: approved,
      message: message,
    );
    if (updated == null) {
      return ShellActionOutcome.failure(feed.errorMessage ?? '审批任务失败');
    }
    await Future.wait([
      _dashboardViewModel.loadSummary(),
      _approvalQueueViewModel.loadQueue(),
      if (job.controlTaskId != null) _controlTaskViewModel.loadControlTasks(),
    ]);
    await _openOperation(updated);
    return ShellActionOutcome.success(
      approved ? '已批准任务: ${job.displayTitle}' : '已驳回任务: ${job.displayTitle}',
      data: updated,
      tone: approved ? ShellActionTone.success : ShellActionTone.warning,
    );
  }

  JobViewModel? _feedFor(JobRecord job) {
    final key = switch (job.type) {
      'optimization' => JobFeedKey.optimization,
      'analysis' => JobFeedKey.analysis,
      'ml_train' => JobFeedKey.mlTrain,
      'rag_ingest' => JobFeedKey.ragIngest,
      _ => null,
    };
    return key == null ? null : _jobFeedRegistry.feedFor(key);
  }

  Future<void> _openOperation(JobRecord operation) {
    return _operationConsoleViewModel.selectOperation(
      operation.operationId ?? operation.jobId,
      seed: operation,
    );
  }
}
