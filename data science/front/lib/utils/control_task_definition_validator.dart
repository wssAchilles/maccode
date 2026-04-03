/// Validation helpers for planning-layer task definitions.
library;

import 'dart:convert';

import '../models/control_task_schedule_draft.dart';

final RegExp _hourlySchedulePattern = RegExp(
  r'^every\s+([1-9]\d*)\s+hours?$',
  caseSensitive: false,
);
final RegExp _dailySchedulePattern = RegExp(
  r'^every\s+day\s+([01]\d|2[0-3]):([0-5]\d)(?:\s+UTC)?$',
  caseSensitive: false,
);
final RegExp _timeTextPattern = RegExp(r'^([01]\d|2[0-3]):([0-5]\d)$');
final RegExp _dependencyPattern = RegExp(r'^[A-Za-z][A-Za-z0-9_:-]{0,63}$');

ControlTaskScheduleDraft parseControlTaskScheduleDraft(String? raw) {
  final normalized = raw?.trim() ?? '';
  if (normalized.isEmpty || normalized.toLowerCase() == 'manual') {
    return const ControlTaskScheduleDraft(mode: ControlTaskScheduleMode.manual);
  }

  final hourlyMatch = _hourlySchedulePattern.firstMatch(normalized);
  if (hourlyMatch != null) {
    return ControlTaskScheduleDraft(
      mode: ControlTaskScheduleMode.hourly,
      intervalText: hourlyMatch.group(1) ?? '1',
    );
  }

  final dailyMatch = _dailySchedulePattern.firstMatch(normalized);
  if (dailyMatch != null) {
    return ControlTaskScheduleDraft(
      mode: ControlTaskScheduleMode.daily,
      timeText: '${dailyMatch.group(1)}:${dailyMatch.group(2)}',
    );
  }

  return ControlTaskScheduleDraft(
    mode: ControlTaskScheduleMode.custom,
    customText: normalized,
  );
}

String formatControlTaskScheduleDraft(ControlTaskScheduleDraft draft) {
  switch (draft.mode) {
    case ControlTaskScheduleMode.manual:
      return '';
    case ControlTaskScheduleMode.hourly:
      return 'every ${draft.intervalText.trim()} hours';
    case ControlTaskScheduleMode.daily:
      return 'every day ${draft.timeText.trim()} UTC';
    case ControlTaskScheduleMode.custom:
      return draft.customText.trim();
  }
}

String? normalizeControlTaskScheduleInput(String raw) {
  final normalized = raw.trim();
  if (normalized.isEmpty || normalized.toLowerCase() == 'manual') {
    return null;
  }

  final hourlyMatch = _hourlySchedulePattern.firstMatch(normalized);
  if (hourlyMatch != null) {
    return 'every ${hourlyMatch.group(1)} hours';
  }

  final dailyMatch = _dailySchedulePattern.firstMatch(normalized);
  if (dailyMatch != null) {
    return 'every day ${dailyMatch.group(1)}:${dailyMatch.group(2)} UTC';
  }
  return null;
}

String? validateControlTaskScheduleInput(String raw) {
  final normalized = raw.trim();
  if (normalized.isEmpty || normalized.toLowerCase() == 'manual') {
    return null;
  }
  if (normalizeControlTaskScheduleInput(normalized) != null) {
    return null;
  }
  return '仅支持留空、manual、every N hours、every day HH:MM UTC';
}

String? validateControlTaskScheduleDraft(ControlTaskScheduleDraft draft) {
  switch (draft.mode) {
    case ControlTaskScheduleMode.manual:
      return null;
    case ControlTaskScheduleMode.hourly:
      final interval = int.tryParse(draft.intervalText.trim());
      if (interval == null || interval <= 0) {
        return '小时间隔必须是大于 0 的整数';
      }
      return null;
    case ControlTaskScheduleMode.daily:
      if (!_timeTextPattern.hasMatch(draft.timeText.trim())) {
        return '每日调度时间必须是 HH:MM';
      }
      return null;
    case ControlTaskScheduleMode.custom:
      return validateControlTaskScheduleInput(draft.customText);
  }
}

String buildControlTaskSchedulePreview(String raw) {
  final normalized = normalizeControlTaskScheduleInput(raw);
  if (normalized == null) {
    return '手动触发';
  }

  final hourlyMatch = _hourlySchedulePattern.firstMatch(normalized);
  if (hourlyMatch != null) {
    return '每 ${hourlyMatch.group(1)} 小时自动运行一次';
  }

  final dailyMatch = _dailySchedulePattern.firstMatch(normalized);
  if (dailyMatch != null) {
    return '每天 ${dailyMatch.group(1)}:${dailyMatch.group(2)} UTC 自动运行';
  }

  return normalized;
}

String buildControlTaskScheduleDraftPreview(ControlTaskScheduleDraft draft) {
  return buildControlTaskSchedulePreview(formatControlTaskScheduleDraft(draft));
}

List<String> parseControlTaskDependencyEditorValue(String raw) {
  return raw
      .split(RegExp(r'[\n,]+'))
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

String? validateControlTaskDependencyEditorValue(String raw) {
  final items = parseControlTaskDependencyEditorValue(raw);
  final seen = <String>{};
  for (final item in items) {
    if (!_dependencyPattern.hasMatch(item)) {
      return '依赖标识只能包含字母、数字、下划线、短横线、冒号，且必须以字母开头';
    }
    if (!seen.add(item)) {
      return '依赖标识重复: $item';
    }
  }
  return null;
}

String? validateControlTaskJsonObjectInput(String raw) {
  final normalized = raw.trim();
  if (normalized.isEmpty) {
    return null;
  }
  try {
    final decoded = jsonDecode(normalized);
    if (decoded is! Map) {
      return '默认输入必须是 JSON 对象';
    }
    return null;
  } catch (_) {
    return '默认输入必须是合法 JSON 对象';
  }
}

Map<String, dynamic> decodeControlTaskJsonObjectInput(String raw) {
  final normalized = raw.trim();
  if (normalized.isEmpty) {
    return <String, dynamic>{};
  }
  final decoded = jsonDecode(normalized);
  if (decoded is! Map) {
    throw const FormatException('默认输入必须是 JSON 对象');
  }
  return Map<String, dynamic>.from(decoded);
}
