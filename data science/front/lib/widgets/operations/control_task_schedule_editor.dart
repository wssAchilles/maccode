/// Structured schedule editor for control tasks.
library;

import 'package:flutter/material.dart';

import '../../models/control_task_schedule_draft.dart';
import '../../utils/control_task_definition_validator.dart';

class ControlTaskScheduleEditor extends StatefulWidget {
  const ControlTaskScheduleEditor({
    super.key,
    required this.initialSchedule,
    required this.onChanged,
  });

  final String? initialSchedule;
  final ValueChanged<String> onChanged;

  @override
  State<ControlTaskScheduleEditor> createState() =>
      _ControlTaskScheduleEditorState();
}

class _ControlTaskScheduleEditorState extends State<ControlTaskScheduleEditor> {
  late ControlTaskScheduleDraft _draft;
  late final TextEditingController _intervalController;
  late final TextEditingController _timeController;
  late final TextEditingController _customController;

  @override
  void initState() {
    super.initState();
    _draft = parseControlTaskScheduleDraft(widget.initialSchedule);
    _intervalController = TextEditingController(text: _draft.intervalText);
    _timeController = TextEditingController(text: _draft.timeText);
    _customController = TextEditingController(text: _draft.customText);
  }

  @override
  void dispose() {
    _intervalController.dispose();
    _timeController.dispose();
    _customController.dispose();
    super.dispose();
  }

  void _emit() {
    widget.onChanged(formatControlTaskScheduleDraft(_draft));
  }

  void _setMode(ControlTaskScheduleMode mode) {
    setState(() {
      _draft = _draft.copyWith(mode: mode);
    });
    _emit();
  }

  void _updateInterval(String value) {
    setState(() {
      _draft = _draft.copyWith(intervalText: value);
    });
    _emit();
  }

  void _updateTime(String value) {
    setState(() {
      _draft = _draft.copyWith(timeText: value);
    });
    _emit();
  }

  void _updateCustom(String value) {
    setState(() {
      _draft = _draft.copyWith(customText: value);
    });
    _emit();
  }

  @override
  Widget build(BuildContext context) {
    final errorText = validateControlTaskScheduleDraft(_draft);
    final previewText = buildControlTaskScheduleDraftPreview(_draft);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<ControlTaskScheduleMode>(
          initialValue: _draft.mode,
          decoration: const InputDecoration(labelText: '调度模式'),
          items: const [
            DropdownMenuItem(
              value: ControlTaskScheduleMode.manual,
              child: Text('手动触发'),
            ),
            DropdownMenuItem(
              value: ControlTaskScheduleMode.hourly,
              child: Text('按小时'),
            ),
            DropdownMenuItem(
              value: ControlTaskScheduleMode.daily,
              child: Text('按天'),
            ),
            DropdownMenuItem(
              value: ControlTaskScheduleMode.custom,
              child: Text('自定义'),
            ),
          ],
          onChanged: (value) {
            if (value != null) {
              _setMode(value);
            }
          },
        ),
        const SizedBox(height: 12),
        if (_draft.mode == ControlTaskScheduleMode.hourly) ...[
          TextFormField(
            controller: _intervalController,
            keyboardType: TextInputType.number,
            onChanged: _updateInterval,
            decoration: InputDecoration(
              labelText: '每隔多少小时',
              hintText: '例如 1 / 4 / 12',
              errorText: errorText,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final preset in ['1', '4', '12'])
                ActionChip(
                  label: Text('$preset 小时'),
                  onPressed: () {
                    _intervalController.text = preset;
                    _updateInterval(preset);
                  },
                ),
            ],
          ),
        ],
        if (_draft.mode == ControlTaskScheduleMode.daily) ...[
          TextFormField(
            controller: _timeController,
            keyboardType: TextInputType.datetime,
            onChanged: _updateTime,
            decoration: InputDecoration(
              labelText: '每日执行时间',
              hintText: 'HH:MM，例如 04:00',
              errorText: errorText,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final preset in ['00:00', '04:00', '08:00', '12:00'])
                ActionChip(
                  label: Text(preset),
                  onPressed: () {
                    _timeController.text = preset;
                    _updateTime(preset);
                  },
                ),
            ],
          ),
        ],
        if (_draft.mode == ControlTaskScheduleMode.custom)
          TextFormField(
            controller: _customController,
            onChanged: _updateCustom,
            decoration: InputDecoration(
              labelText: '自定义调度表达式',
              hintText: 'every 2 hours / every day 04:00 UTC',
              errorText: errorText,
            ),
          ),
        if (_draft.mode == ControlTaskScheduleMode.manual)
          Text(
            '当前任务仅支持手动触发，不会自动调度。',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        const SizedBox(height: 8),
        Text('执行预览：$previewText', style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
