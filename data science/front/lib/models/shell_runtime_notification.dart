library;

import 'shell_action_outcome.dart';
import 'workbench_runtime_models.dart';

enum ShellRuntimeNotificationKind { action, session, alert, runtime }

class ShellRuntimeNotification {
  const ShellRuntimeNotification({
    required this.id,
    required this.kind,
    required this.title,
    required this.message,
    required this.tone,
    required this.createdAt,
    this.sourceTab,
    this.relatedOperationId,
    this.isRead = false,
    this.metadata = const <String, dynamic>{},
  });

  final String id;
  final ShellRuntimeNotificationKind kind;
  final String title;
  final String message;
  final ShellActionTone tone;
  final DateTime createdAt;
  final WorkbenchTab? sourceTab;
  final String? relatedOperationId;
  final bool isRead;
  final Map<String, dynamic> metadata;

  ShellRuntimeNotification copyWith({bool? isRead}) {
    return ShellRuntimeNotification(
      id: id,
      kind: kind,
      title: title,
      message: message,
      tone: tone,
      createdAt: createdAt,
      sourceTab: sourceTab,
      relatedOperationId: relatedOperationId,
      isRead: isRead ?? this.isRead,
      metadata: metadata,
    );
  }
}
