import 'package:flutter_test/flutter_test.dart';

import 'package:front/utils/control_task_definition_validator.dart';

void main() {
  test('normalizes supported schedule formats', () {
    expect(normalizeControlTaskScheduleInput('every 1 hour'), 'every 1 hours');
    expect(
      normalizeControlTaskScheduleInput('every day 04:00'),
      'every day 04:00 UTC',
    );
    expect(normalizeControlTaskScheduleInput('manual'), isNull);
  });

  test('rejects unsupported schedule formats', () {
    expect(
      validateControlTaskScheduleInput('daily at 5'),
      contains('every N hours'),
    );
  });

  test('rejects duplicate dependencies', () {
    expect(
      validateControlTaskDependencyEditorValue('dataset_ready, dataset_ready'),
      contains('重复'),
    );
  });

  test('validates json object input', () {
    expect(validateControlTaskJsonObjectInput('{"ok":true}'), isNull);
    expect(validateControlTaskJsonObjectInput('[]'), contains('JSON 对象'));
  });
}
