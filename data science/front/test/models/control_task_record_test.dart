import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/control_task_record.dart';

void main() {
  test('ControlTaskRecord parses planning-layer fields', () {
    final record = ControlTaskRecord.fromJson(const {
      'id': 'train_model_daily',
      'kind': 'scheduler',
      'operation_type': 'train_model',
      'title': '每日模型重训',
      'schedule': 'every day 04:00 UTC',
      'default_input': {'task_name': 'train_model'},
      'dependencies': ['dataset_ready'],
      'approval_policy': {'required': false, 'mode': 'auto'},
      'enabled': true,
      'owner': 'system',
      'created_at': '2026-04-03T08:00:00Z',
      'updated_at': '2026-04-03T09:00:00Z',
    });

    expect(record.id, 'train_model_daily');
    expect(record.kind, 'scheduler');
    expect(record.operationType, 'train_model');
    expect(record.defaultInput['task_name'], 'train_model');
    expect(record.dependencies, ['dataset_ready']);
    expect(record.approvalPolicy['mode'], 'auto');
    expect(record.enabled, isTrue);
    expect(record.owner, 'system');
    expect(record.updatedAt, isNotNull);
  });

  test('ControlTaskRecord parses runtime enrichment fields', () {
    final record = ControlTaskRecord.fromJson(const {
      'id': 'train_model_daily',
      'kind': 'scheduler',
      'title': '每日模型重训',
      'enabled': true,
      'next_run_at': '2026-04-04T04:00:00Z',
      'dependency_state': 'ready',
      'dependency_summary': '依赖已就绪',
      'dependency_details': [
        {'id': 'dataset_ready', 'state': 'ready', 'title': '数据已准备'},
      ],
      'latest_operation': {
        'operation_id': 'op-1',
        'type': 'train_model',
        'status': 'awaiting_approval',
        'progress': 30,
        'submitted_at': '2026-04-03T10:00:00Z',
      },
    });

    expect(record.nextRunAt, isNotNull);
    expect(record.dependencyState, 'ready');
    expect(record.dependencySummary, '依赖已就绪');
    expect(record.dependencyDetails, hasLength(1));
    expect(record.dependencyDetails.first.title, '数据已准备');
    expect(record.latestOperation, isNotNull);
    expect(record.latestOperation!.operationId, 'op-1');
    expect(record.latestOperation!.status, 'awaiting_approval');
    expect(record.latestOperation!.progress, 30);
  });
}
