/// Structured editor state for control-task schedules.
library;

enum ControlTaskScheduleMode { manual, hourly, daily, custom }

class ControlTaskScheduleDraft {
  const ControlTaskScheduleDraft({
    required this.mode,
    this.intervalText = '1',
    this.timeText = '04:00',
    this.customText = '',
  });

  final ControlTaskScheduleMode mode;
  final String intervalText;
  final String timeText;
  final String customText;

  ControlTaskScheduleDraft copyWith({
    ControlTaskScheduleMode? mode,
    String? intervalText,
    String? timeText,
    String? customText,
  }) {
    return ControlTaskScheduleDraft(
      mode: mode ?? this.mode,
      intervalText: intervalText ?? this.intervalText,
      timeText: timeText ?? this.timeText,
      customText: customText ?? this.customText,
    );
  }
}
