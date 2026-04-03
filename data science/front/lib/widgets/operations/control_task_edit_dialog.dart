/// 规划任务定义编辑弹窗
library;

import 'dart:convert';

import 'package:flutter/material.dart';

import '../../models/control_task_record.dart';
import '../../utils/control_task_definition_validator.dart';

class ControlTaskDefinitionDraft {
  const ControlTaskDefinitionDraft({
    required this.schedule,
    required this.owner,
    required this.dependencies,
    required this.approvalPolicy,
    required this.defaultInput,
  });

  final String? schedule;
  final String owner;
  final List<String> dependencies;
  final Map<String, dynamic> approvalPolicy;
  final Map<String, dynamic> defaultInput;
}

Future<ControlTaskDefinitionDraft?> showControlTaskEditDialog(
  BuildContext context,
  ControlTaskRecord task,
) {
  return showDialog<ControlTaskDefinitionDraft>(
    context: context,
    builder: (context) => _ControlTaskEditDialog(task: task),
  );
}

class _ControlTaskEditDialog extends StatefulWidget {
  const _ControlTaskEditDialog({required this.task});

  final ControlTaskRecord task;

  @override
  State<_ControlTaskEditDialog> createState() => _ControlTaskEditDialogState();
}

class _ControlTaskEditDialogState extends State<_ControlTaskEditDialog> {
  late final TextEditingController _scheduleController;
  late final TextEditingController _ownerController;
  late final TextEditingController _dependenciesController;
  late final TextEditingController _approvalReasonController;
  late final TextEditingController _defaultInputController;
  late bool _approvalRequired;
  String? _errorText;

  @override
  void initState() {
    super.initState();
    _scheduleController = TextEditingController(
      text: widget.task.schedule ?? '',
    );
    _ownerController = TextEditingController(
      text: widget.task.owner.isEmpty ? 'system' : widget.task.owner,
    );
    _dependenciesController = TextEditingController(
      text: widget.task.dependencies.join(', '),
    );
    _approvalRequired = widget.task.approvalPolicy['required'] == true;
    _approvalReasonController = TextEditingController(
      text: (widget.task.approvalPolicy['reason'] ?? '').toString(),
    );
    _defaultInputController = TextEditingController(
      text: const JsonEncoder.withIndent(
        '  ',
      ).convert(widget.task.defaultInput),
    );
  }

  @override
  void dispose() {
    _scheduleController.dispose();
    _ownerController.dispose();
    _dependenciesController.dispose();
    _approvalReasonController.dispose();
    _defaultInputController.dispose();
    super.dispose();
  }

  void _submit() {
    final scheduleError = validateControlTaskScheduleInput(
      _scheduleController.text,
    );
    final dependencyError = validateControlTaskDependencyEditorValue(
      _dependenciesController.text,
    );
    final jsonError = validateControlTaskJsonObjectInput(
      _defaultInputController.text,
    );
    if (scheduleError != null || dependencyError != null || jsonError != null) {
      setState(() {
        _errorText = scheduleError ?? dependencyError ?? jsonError;
      });
      return;
    }

    final owner = _ownerController.text.trim();
    final dependencies = parseControlTaskDependencyEditorValue(
      _dependenciesController.text,
    );
    final approvalReason = _approvalReasonController.text.trim();

    try {
      Navigator.of(context).pop(
        ControlTaskDefinitionDraft(
          schedule: normalizeControlTaskScheduleInput(_scheduleController.text),
          owner: owner.isEmpty ? 'system' : owner,
          dependencies: dependencies,
          approvalPolicy: _buildApprovalPolicy(
            required: _approvalRequired,
            reason: approvalReason,
          ),
          defaultInput: decodeControlTaskJsonObjectInput(
            _defaultInputController.text,
          ),
        ),
      );
    } on FormatException catch (error) {
      setState(() {
        _errorText = error.message;
      });
    } catch (_) {
      setState(() {
        _errorText = '默认输入必须是合法 JSON 对象';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheduleError = validateControlTaskScheduleInput(
      _scheduleController.text,
    );
    final dependencyError = validateControlTaskDependencyEditorValue(
      _dependenciesController.text,
    );
    final jsonError = validateControlTaskJsonObjectInput(
      _defaultInputController.text,
    );
    final schedulePreview = buildControlTaskSchedulePreview(
      _scheduleController.text,
    );
    final dependencies = parseControlTaskDependencyEditorValue(
      _dependenciesController.text,
    );
    final canSubmit =
        scheduleError == null && dependencyError == null && jsonError == null;

    return AlertDialog(
      title: Text('编辑规划任务: ${widget.task.title}'),
      content: SizedBox(
        width: 520,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextFormField(
                controller: _scheduleController,
                onChanged: (_) => setState(() => _errorText = null),
                decoration: InputDecoration(
                  labelText: '调度策略',
                  hintText: '留空表示仅手动触发',
                  errorText: scheduleError,
                  helperText: '支持 every N hours 或 every day HH:MM UTC',
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '执行预览：$schedulePreview',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _ownerController,
                onChanged: (_) => setState(() => _errorText = null),
                decoration: const InputDecoration(
                  labelText: '责任人',
                  hintText: '例如 mlops / dataops / system',
                ),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _dependenciesController,
                onChanged: (_) => setState(() => _errorText = null),
                minLines: 2,
                maxLines: 4,
                decoration: InputDecoration(
                  labelText: '依赖列表',
                  hintText: '使用逗号或换行分隔，例如 dataset_ready, weather_ready',
                  alignLabelWithHint: true,
                  errorText: dependencyError,
                  helperText: dependencies.isEmpty
                      ? '当前没有依赖'
                      : '当前识别到 ${dependencies.length} 个依赖',
                ),
              ),
              const SizedBox(height: 12),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('需要审批'),
                subtitle: const Text('高成本或高风险动作先进入待审批状态'),
                value: _approvalRequired,
                onChanged: (value) {
                  setState(() {
                    _errorText = null;
                    _approvalRequired = value;
                  });
                },
              ),
              const SizedBox(height: 4),
              TextFormField(
                controller: _approvalReasonController,
                onChanged: (_) => setState(() => _errorText = null),
                minLines: 2,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: '审批原因',
                  hintText: '例如：覆盖现有模型产物需要审批',
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _defaultInputController,
                onChanged: (_) => setState(() => _errorText = null),
                minLines: 6,
                maxLines: 10,
                decoration: InputDecoration(
                  labelText: '默认输入 JSON',
                  alignLabelWithHint: true,
                  errorText: jsonError,
                ),
              ),
              if (_errorText != null) ...[
                const SizedBox(height: 12),
                Text(
                  _errorText!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('取消'),
        ),
        FilledButton(
          onPressed: canSubmit ? _submit : null,
          child: const Text('保存'),
        ),
      ],
    );
  }
}

Map<String, dynamic> _buildApprovalPolicy({
  required bool required,
  required String reason,
}) {
  final normalizedReason = reason.trim();
  return <String, dynamic>{
    'required': required,
    'mode': required ? 'manual' : 'auto',
    if (normalizedReason.isNotEmpty) 'reason': normalizedReason,
  };
}
