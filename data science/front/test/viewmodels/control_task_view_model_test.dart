import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/control_task_record.dart';
import 'package:front/models/job_record.dart';
import 'package:front/repositories/control_task_repository.dart';
import 'package:front/services/api_service_exception.dart';
import 'package:front/viewmodels/control_task_view_model.dart';

class _FakeControlTaskRepository implements ControlTaskRepository {
  _FakeControlTaskRepository({
    this.tasks = const <ControlTaskRecord>[],
    this.error,
    this.updatedTask,
    this.approvalUpdatedTask,
    this.definitionUpdatedTask,
  });

  final List<ControlTaskRecord> tasks;
  final Object? error;
  final ControlTaskRecord? updatedTask;
  final ControlTaskRecord? approvalUpdatedTask;
  final ControlTaskRecord? definitionUpdatedTask;

  @override
  Future<ControlTaskRecord> getControlTask(String controlTaskId) async {
    return tasks.firstWhere((task) => task.id == controlTaskId);
  }

  @override
  Future<JobRecord> runControlTask(
    String controlTaskId, {
    Map<String, dynamic>? input,
    String trigger = 'manual',
  }) async {
    if (error != null) {
      throw error!;
    }
    return const JobRecord(
      jobId: 'op-1',
      operationId: 'op-1',
      type: 'analysis',
      status: 'queued',
      progress: 0,
      requestedBy: 'tester',
      attemptCount: 0,
      maxAttempts: 3,
    );
  }

  @override
  Future<ControlTaskRecord> setControlTaskEnabled(
    String controlTaskId, {
    required bool enabled,
  }) async {
    if (error != null) {
      throw error!;
    }
    return updatedTask ??
        ControlTaskRecord(
          id: controlTaskId,
          kind: 'scheduler',
          operationType: 'train_model',
          title: '每日模型重训',
          enabled: enabled,
        );
  }

  @override
  Future<ControlTaskRecord> setControlTaskApprovalPolicy(
    String controlTaskId, {
    required Map<String, dynamic> approvalPolicy,
  }) async {
    if (error != null) {
      throw error!;
    }
    return approvalUpdatedTask ??
        ControlTaskRecord(
          id: controlTaskId,
          kind: 'scheduler',
          operationType: 'train_model',
          title: '每日模型重训',
          enabled: true,
          approvalPolicy: approvalPolicy,
        );
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
    if (error != null) {
      throw error!;
    }
    return definitionUpdatedTask ??
        ControlTaskRecord(
          id: controlTaskId,
          kind: 'scheduler',
          operationType: 'train_model',
          title: '每日模型重训',
          enabled: true,
          schedule: schedule,
          owner: owner ?? 'system',
          dependencies: dependencies,
          approvalPolicy: approvalPolicy,
          defaultInput: defaultInput,
        );
  }

  @override
  Future<List<ControlTaskRecord>> listControlTasks({
    String? kind,
    bool? enabled,
    String? owner,
    int limit = 20,
  }) async {
    if (error != null) {
      throw error!;
    }
    return tasks.take(limit).toList(growable: false);
  }
}

void main() {
  test('loadControlTasks stores returned planning tasks', () async {
    final viewModel = ControlTaskViewModel(
      repository: _FakeControlTaskRepository(
        tasks: const [
          ControlTaskRecord(
            id: 'fetch_data_hourly',
            kind: 'scheduler',
            title: '每小时抓取',
            enabled: true,
          ),
        ],
      ),
    );

    await viewModel.loadControlTasks();

    expect(viewModel.tasks, hasLength(1));
    expect(viewModel.tasks.single.id, 'fetch_data_hourly');
    expect(viewModel.errorMessage, isNull);
    viewModel.dispose();
  });

  test('loadControlTasks exposes readable error message', () async {
    final viewModel = ControlTaskViewModel(
      repository: _FakeControlTaskRepository(
        error: const ApiServiceException('backend unavailable'),
      ),
    );

    await viewModel.loadControlTasks();

    expect(viewModel.tasks, isEmpty);
    expect(viewModel.errorMessage, contains('backend unavailable'));
    viewModel.dispose();
  });

  test(
    'runControlTask tracks in-flight state and returns launched operation',
    () async {
      final viewModel = ControlTaskViewModel(
        repository: _FakeControlTaskRepository(
          tasks: const [
            ControlTaskRecord(
              id: 'train_model_daily',
              kind: 'scheduler',
              operationType: 'train_model',
              title: '每日模型重训',
            ),
          ],
        ),
      );

      final task = viewModel.tasks.isEmpty
          ? const ControlTaskRecord(
              id: 'train_model_daily',
              kind: 'scheduler',
              operationType: 'train_model',
              title: '每日模型重训',
            )
          : viewModel.tasks.first;

      final operation = await viewModel.runControlTask(task);

      expect(operation, isNotNull);
      expect(operation!.status, 'queued');
      expect(viewModel.isRunningTask(task.id), isFalse);
      expect(viewModel.errorMessage, isNull);
      viewModel.dispose();
    },
  );

  test('setControlTaskEnabled updates local task projection', () async {
    final viewModel = ControlTaskViewModel(
      repository: _FakeControlTaskRepository(
        tasks: const [
          ControlTaskRecord(
            id: 'train_model_daily',
            kind: 'scheduler',
            operationType: 'train_model',
            title: '每日模型重训',
            enabled: true,
          ),
        ],
        updatedTask: const ControlTaskRecord(
          id: 'train_model_daily',
          kind: 'scheduler',
          operationType: 'train_model',
          title: '每日模型重训',
          enabled: false,
        ),
      ),
    );

    await viewModel.loadControlTasks();
    final updated = await viewModel.setControlTaskEnabled(
      viewModel.tasks.first,
      enabled: false,
    );

    expect(updated, isNotNull);
    expect(updated!.enabled, isFalse);
    expect(viewModel.tasks.first.enabled, isFalse);
    expect(viewModel.isUpdatingTask(updated.id), isFalse);
    expect(viewModel.errorMessage, isNull);
    viewModel.dispose();
  });

  test('setControlTaskApprovalPolicy updates local approval policy', () async {
    final viewModel = ControlTaskViewModel(
      repository: _FakeControlTaskRepository(
        tasks: const [
          ControlTaskRecord(
            id: 'train_model_daily',
            kind: 'scheduler',
            operationType: 'train_model',
            title: '每日模型重训',
            enabled: true,
            approvalPolicy: {'required': false, 'mode': 'auto'},
          ),
        ],
        approvalUpdatedTask: const ControlTaskRecord(
          id: 'train_model_daily',
          kind: 'scheduler',
          operationType: 'train_model',
          title: '每日模型重训',
          enabled: true,
          approvalPolicy: {'required': true, 'mode': 'manual'},
        ),
      ),
    );

    await viewModel.loadControlTasks();
    final updated = await viewModel.setControlTaskApprovalPolicy(
      viewModel.tasks.first,
      approvalPolicy: const {'required': true, 'mode': 'manual'},
    );

    expect(updated, isNotNull);
    expect(updated!.approvalPolicy['required'], isTrue);
    expect(viewModel.tasks.first.approvalPolicy['mode'], 'manual');
    expect(viewModel.errorMessage, isNull);
    viewModel.dispose();
  });

  test(
    'updateControlTaskDefinition updates local planning definition',
    () async {
      final viewModel = ControlTaskViewModel(
        repository: _FakeControlTaskRepository(
          tasks: const [
            ControlTaskRecord(
              id: 'train_model_daily',
              kind: 'scheduler',
              operationType: 'train_model',
              title: '每日模型重训',
              enabled: true,
              schedule: 'every day 04:00 UTC',
              owner: 'system',
              defaultInput: {'window_days': 30},
            ),
          ],
          definitionUpdatedTask: const ControlTaskRecord(
            id: 'train_model_daily',
            kind: 'scheduler',
            operationType: 'train_model',
            title: '每日模型重训',
            enabled: true,
            schedule: 'every day 05:00 UTC',
            owner: 'mlops',
            dependencies: ['dataset_ready', 'weather_ready'],
            approvalPolicy: {
              'required': true,
              'mode': 'manual',
              'reason': '高成本重训需要审批',
            },
            defaultInput: {'window_days': 60},
          ),
        ),
      );

      await viewModel.loadControlTasks();
      final updated = await viewModel.updateControlTaskDefinition(
        viewModel.tasks.first,
        schedule: 'every day 05:00 UTC',
        owner: 'mlops',
        dependencies: const ['dataset_ready', 'weather_ready'],
        approvalPolicy: const {
          'required': true,
          'mode': 'manual',
          'reason': '高成本重训需要审批',
        },
        defaultInput: const {'window_days': 60},
      );

      expect(updated, isNotNull);
      expect(updated!.schedule, 'every day 05:00 UTC');
      expect(viewModel.tasks.first.owner, 'mlops');
      expect(viewModel.tasks.first.dependencies, [
        'dataset_ready',
        'weather_ready',
      ]);
      expect(viewModel.tasks.first.approvalPolicy['reason'], '高成本重训需要审批');
      expect(viewModel.tasks.first.defaultInput['window_days'], 60);
      expect(viewModel.errorMessage, isNull);
      viewModel.dispose();
    },
  );
}
