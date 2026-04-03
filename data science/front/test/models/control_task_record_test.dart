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
}
