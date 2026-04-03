import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/control_task_schedule_draft.dart';
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

  test('parses and formats structured schedule drafts', () {
    final daily = parseControlTaskScheduleDraft('every day 04:00 UTC');
    expect(daily.mode, ControlTaskScheduleMode.daily);
    expect(daily.timeText, '04:00');
    expect(formatControlTaskScheduleDraft(daily), 'every day 04:00 UTC');

    final hourly = const ControlTaskScheduleDraft(
      mode: ControlTaskScheduleMode.hourly,
      intervalText: '4',
    );
    expect(validateControlTaskScheduleDraft(hourly), isNull);
    expect(buildControlTaskScheduleDraftPreview(hourly), contains('4 小时'));
  });

  test('validates json object input', () {
    expect(validateControlTaskJsonObjectInput('{"ok":true}'), isNull);
    expect(validateControlTaskJsonObjectInput('[]'), contains('JSON 对象'));
  });
}
