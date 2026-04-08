library;

import 'shell_action_outcome.dart';
import 'shell_runtime_intent.dart';

enum ShellActionPhase {
  idle,
  submitting,
  awaitingApproval,
  succeeded,
  failed,
  replaying,
}

class ShellRuntimeActionState {
  const ShellRuntimeActionState({
    required this.intent,
    required this.phase,
    required this.startedAt,
    this.completedAt,
    this.message,
    this.tone = ShellActionTone.info,
    this.relatedOperationId,
  });

  final ShellRuntimeIntent intent;
  final ShellActionPhase phase;
  final DateTime startedAt;
  final DateTime? completedAt;
  final String? message;
  final ShellActionTone tone;
  final String? relatedOperationId;

  bool get isActive =>
      phase == ShellActionPhase.submitting ||
      phase == ShellActionPhase.replaying;

  String get phaseLabel {
    switch (phase) {
      case ShellActionPhase.idle:
        return '待命';
      case ShellActionPhase.submitting:
        return '执行中';
      case ShellActionPhase.awaitingApproval:
        return '待审批';
      case ShellActionPhase.succeeded:
        return '已完成';
      case ShellActionPhase.failed:
        return '失败';
      case ShellActionPhase.replaying:
        return '重放中';
    }
  }

  ShellRuntimeActionState copyWith({
    ShellActionPhase? phase,
    DateTime? completedAt,
    String? message,
    ShellActionTone? tone,
    String? relatedOperationId,
  }) {
    return ShellRuntimeActionState(
      intent: intent,
      phase: phase ?? this.phase,
      startedAt: startedAt,
      completedAt: completedAt ?? this.completedAt,
      message: message ?? this.message,
      tone: tone ?? this.tone,
      relatedOperationId: relatedOperationId ?? this.relatedOperationId,
    );
  }
}
