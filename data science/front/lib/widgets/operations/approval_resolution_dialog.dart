/// Approval message dialog for governance actions.
library;

import 'package:flutter/material.dart';

Future<String?> showApprovalResolutionDialog(
  BuildContext context, {
  required bool approved,
  required String title,
}) {
  return showDialog<String>(
    context: context,
    builder: (context) =>
        _ApprovalResolutionDialog(approved: approved, title: title),
  );
}

class _ApprovalResolutionDialog extends StatefulWidget {
  const _ApprovalResolutionDialog({
    required this.approved,
    required this.title,
  });

  final bool approved;
  final String title;

  @override
  State<_ApprovalResolutionDialog> createState() =>
      _ApprovalResolutionDialogState();
}

class _ApprovalResolutionDialogState extends State<_ApprovalResolutionDialog> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final actionLabel = widget.approved ? '批准执行' : '驳回任务';
    final helper = widget.approved
        ? '可以填写批准原因、预算说明或审批人备注。'
        : '建议填写驳回原因，便于后续审计和重试治理。';
    return AlertDialog(
      title: Text('$actionLabel · ${widget.title}'),
      content: SizedBox(
        width: 460,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(helper),
            const SizedBox(height: 12),
            TextField(
              controller: _controller,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: '审批备注',
                hintText: '例如：已确认预算和产物覆盖范围',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('取消'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(_controller.text.trim()),
          child: Text(actionLabel),
        ),
      ],
    );
  }
}
