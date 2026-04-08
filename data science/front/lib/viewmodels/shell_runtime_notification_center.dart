library;

import 'package:flutter/foundation.dart';

import '../models/dashboard_summary.dart';
import '../models/job_record.dart';
import '../models/shell_action_outcome.dart';
import '../models/shell_operation_session.dart';
import '../models/shell_runtime_intent.dart';
import '../models/shell_runtime_notification.dart';
import '../models/workbench_runtime_models.dart';

class ShellRuntimeNotificationCenter extends ChangeNotifier {
  static const int _notificationLimit = 24;

  final List<ShellRuntimeNotification> _notifications =
      <ShellRuntimeNotification>[];
  final Set<String> _knownAlertKeys = <String>{};
  String? _lastSessionFingerprint;

  List<ShellRuntimeNotification> get notifications =>
      List.unmodifiable(_notifications);
  int get unreadCount => _notifications.where((item) => !item.isRead).length;

  void recordActionOutcome<T>(
    ShellRuntimeIntent intent,
    ShellActionOutcome<T> outcome,
  ) {
    final relatedOperationId = _extractOperationId(intent, outcome.data);
    _push(
      ShellRuntimeNotification(
        id: 'action-${intent.id}',
        kind: ShellRuntimeNotificationKind.action,
        title: intent.label,
        message: outcome.message,
        tone: outcome.tone,
        createdAt: DateTime.now(),
        sourceTab: intent.sourceTab,
        relatedOperationId: relatedOperationId,
        metadata: <String, dynamic>{
          'domain': intent.domain.name,
          'kind': intent.kind.name,
          'resource_id': intent.resourceId,
        },
      ),
    );
  }

  void recordBackendAlerts(
    List<DashboardAlert> alerts, {
    required WorkbenchTab sourceTab,
  }) {
    for (final alert in alerts) {
      final dedupeKey = '${alert.severity}:${alert.title}:${alert.message}';
      if (_knownAlertKeys.contains(dedupeKey)) {
        continue;
      }
      _knownAlertKeys.add(dedupeKey);
      _push(
        ShellRuntimeNotification(
          id: 'alert-$dedupeKey',
          kind: ShellRuntimeNotificationKind.alert,
          title: alert.title,
          message: alert.message,
          tone: _toneForSeverity(alert.severity),
          createdAt: DateTime.now(),
          sourceTab: sourceTab,
          metadata: <String, dynamic>{
            'severity': alert.severity,
          },
        ),
      );
    }
  }

  void recordSessionUpdate(ShellOperationSession session) {
    final operationId = session.operationId;
    if (operationId == null || operationId.isEmpty) {
      return;
    }
    if (session.phase != ShellOperationSessionPhase.awaitingApproval &&
        session.phase != ShellOperationSessionPhase.terminal &&
        session.phase != ShellOperationSessionPhase.error) {
      return;
    }
    final transitionAt = session.lastUpdatedAt?.toIso8601String() ?? '';
    final fingerprint = '$operationId:${session.phase.name}:$transitionAt';
    if (_lastSessionFingerprint == fingerprint) {
      return;
    }
    _lastSessionFingerprint = fingerprint;
    _push(
      ShellRuntimeNotification(
        id: 'session-$fingerprint',
        kind: ShellRuntimeNotificationKind.session,
        title: _sessionTitle(session),
        message:
            session.latestMessage ??
            session.errorMessage ??
            session.statusLabel,
        tone: _toneForSessionPhase(session.phase),
        createdAt: DateTime.now(),
        sourceTab: session.originTab,
        relatedOperationId: operationId,
        metadata: <String, dynamic>{
          'phase': session.phase.name,
          'operation_id': operationId,
        },
      ),
    );
  }

  void markRead(String notificationId) {
    final index = _notifications.indexWhere((item) => item.id == notificationId);
    if (index == -1) {
      return;
    }
    _notifications[index] = _notifications[index].copyWith(isRead: true);
    notifyListeners();
  }

  void markAllRead() {
    for (var index = 0; index < _notifications.length; index += 1) {
      _notifications[index] = _notifications[index].copyWith(isRead: true);
    }
    notifyListeners();
  }

  void dismiss(String notificationId) {
    _notifications.removeWhere((item) => item.id == notificationId);
    notifyListeners();
  }

  void _push(ShellRuntimeNotification notification) {
    _notifications.removeWhere((item) => item.id == notification.id);
    _notifications.insert(0, notification);
    if (_notifications.length > _notificationLimit) {
      _notifications.removeRange(_notificationLimit, _notifications.length);
    }
    notifyListeners();
  }

  ShellActionTone _toneForSeverity(String severity) {
    switch (severity) {
      case 'critical':
      case 'error':
        return ShellActionTone.error;
      case 'warning':
        return ShellActionTone.warning;
      case 'success':
        return ShellActionTone.success;
      default:
        return ShellActionTone.info;
    }
  }

  ShellActionTone _toneForSessionPhase(ShellOperationSessionPhase phase) {
    switch (phase) {
      case ShellOperationSessionPhase.awaitingApproval:
        return ShellActionTone.warning;
      case ShellOperationSessionPhase.error:
        return ShellActionTone.error;
      case ShellOperationSessionPhase.terminal:
        return ShellActionTone.success;
      case ShellOperationSessionPhase.idle:
      case ShellOperationSessionPhase.loading:
      case ShellOperationSessionPhase.live:
      case ShellOperationSessionPhase.acting:
        return ShellActionTone.info;
    }
  }

  String _sessionTitle(ShellOperationSession session) {
    switch (session.phase) {
      case ShellOperationSessionPhase.awaitingApproval:
        return '运行进入待审批';
      case ShellOperationSessionPhase.error:
        return '运行会话异常';
      case ShellOperationSessionPhase.terminal:
        return '运行结束';
      case ShellOperationSessionPhase.idle:
      case ShellOperationSessionPhase.loading:
      case ShellOperationSessionPhase.live:
      case ShellOperationSessionPhase.acting:
        return '运行状态更新';
    }
  }

  String? _extractOperationId<T>(ShellRuntimeIntent intent, T? data) {
    if (data is JobRecord) {
      return data.operationId ?? data.jobId;
    }
    if (intent.domain == ShellIntentDomain.operation ||
        intent.domain == ShellIntentDomain.approval) {
      return intent.resourceId;
    }
    return null;
  }
}
