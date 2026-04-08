library;

import 'job_record.dart';
import 'workbench_runtime_models.dart';

enum ShellOperationSessionPhase {
  idle,
  loading,
  live,
  acting,
  awaitingApproval,
  terminal,
  error,
}

class ShellOperationSession {
  const ShellOperationSession({
    required this.sessionId,
    required this.phase,
    this.operationId,
    this.originTab,
    this.openedAt,
    this.lastUpdatedAt,
    this.operation,
    this.latestMessage,
    this.errorMessage,
    this.streaming = false,
    this.retainedAcrossTabs = true,
  });

  const ShellOperationSession.idle()
    : sessionId = '',
      phase = ShellOperationSessionPhase.idle,
      operationId = null,
      originTab = null,
      openedAt = null,
      lastUpdatedAt = null,
      operation = null,
      latestMessage = null,
      errorMessage = null,
      streaming = false,
      retainedAcrossTabs = true;

  final String sessionId;
  final String? operationId;
  final WorkbenchTab? originTab;
  final DateTime? openedAt;
  final DateTime? lastUpdatedAt;
  final ShellOperationSessionPhase phase;
  final JobRecord? operation;
  final String? latestMessage;
  final String? errorMessage;
  final bool streaming;
  final bool retainedAcrossTabs;

  bool get hasSelection => operationId != null;

  String get statusLabel {
    switch (phase) {
      case ShellOperationSessionPhase.idle:
        return '未选中运行';
      case ShellOperationSessionPhase.loading:
        return '载入运行中';
      case ShellOperationSessionPhase.live:
        return streaming ? '实时跟踪中' : '运行已选中';
      case ShellOperationSessionPhase.acting:
        return '执行控制动作中';
      case ShellOperationSessionPhase.awaitingApproval:
        return '等待审批';
      case ShellOperationSessionPhase.terminal:
        return '运行已结束';
      case ShellOperationSessionPhase.error:
        return '运行会话异常';
    }
  }
}
